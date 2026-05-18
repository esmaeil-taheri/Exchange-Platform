from decimal import Decimal
from django.db import transaction

from apps.customers.models.customer import Customer
from apps.customers.exceptions.customer_exceptions import CustomerSuspended
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.exchange.exceptions.currency_exceptions import CurrencyNotBuyable
from apps.exchange.exceptions.exchange_exceptions import InsufficientSystemBalance, InsufficientUserBalance, VerifiedBankCardNotFound
from apps.exchange.services.daily_limit_services import DailyLimitService
from apps.exchange.services.currency_balance_service import CurrencyBalanceService
from apps.exchange.selectors.currency_selectors import CurrencySelector
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.core.exceptions.base import ActionDisabled
from apps.core.utils.date_time_utils import get_date_time
from apps.core.utils.security_utils import get_client_ip
from apps.exchange.services.transaction_service import TransactionService
from apps.exchange.services.wallet_service import WalletService
from apps.exchange.selectors.transaction_selectors import TransactionSelector
from apps.payments.services.payments_services import PaymentService
from apps.customers.selectors.bank_card_selectors import BankCardSelectors

from .price_services import PriceService
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeService:

    @staticmethod
    def buy_asset(request, asset: str, amount: int, buy_from_wallet: bool) -> dict:
        """
        Handles user-initiated gold purchase requests and creates a pending buy transaction.

        This method performs all validation required at the API layer, including:
        - Checking global and currency-specific buy availability.
        - Ensuring no existing pending transaction exists for the user.
        - Enforcing daily buy limits.
        - Validating system inventory (available XAU) and user wallet balance when buying from wallet.
        - Creating both the wallet entry (debit) and the pending transaction inside a single atomic block.

        All actual settlement and gold delivery operations occur later in background workers.
        This method only registers the user's intent and guarantees the request is safe,
        consistent, and ready for asynchronous processing.

        Parameters:
            request (HttpRequest):
                The authenticated request object containing the current user.
            asset (str):
                The asset symbol (e.g., "XAU18") the user intends to purchase.
            amount (int):
                The human-input amount for purchase flow. Internally interpreted
                through `calculate_xau18_currency_price` to compute gold_amount,
                fees, maintenance, and total IRT cost.
            buy_from_wallet (bool):
                If True, the total IRT amount will be debited immediately from the
                user's wallet during this request (atomic). If False, an external
                payment flow is expected.

        Returns:
            dict:
                A simple acknowledgment dictionary, e.g.:
                {"message": "درخواست خرید با موفقیت ثبت شد"}

        Raises:
            CurrencyNotBuyable:
                - If buy operations are globally disabled.
                - If the selected currency is not currently buyable.
            ActionDisabled:
                - If the user already has a pending transaction for this currency.
                - If buying from wallet is disabled for this asset.
            InsufficientSystemBalance:
                - If the system's gold inventory is insufficient for the requested amount.
            InsufficientUserBalance:
                - If the user's IRT wallet does not have enough funds for the purchase.
            ValidationError / Other domain exceptions:
                - If daily limits or business rules are violated.

        Notes:
            - All inventory checks and wallet debit operations happen inside a single
            `transaction.atomic()` block to ensure consistency and prevent race conditions.
            - The resulting transaction will be in `pending` status until the background worker
            processes pricing validation, settlement, and ledger-safe balance updates.
        """

        user_id = request.user.id
        logger.info(
            f"Buy request initiated | user_id={user_id} asset={asset} "
            f"amount={amount} method={'wallet' if buy_from_wallet else 'gateway'}"
        )

        site_settings = get_site_settings()
        if not site_settings.is_buy:
            logger.warning(f"Buy blocked — globally disabled | user_id={user_id} asset={asset}")
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        currency = CurrencySelector.get_currency_by_symbol(symbol=asset)
        if not currency.is_buy:
            logger.warning(f"Buy blocked — currency disabled | user_id={user_id} asset={asset}")
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        calculated_price = PriceService.calculate_xau18_currency_price(
            unit='IRT',
            amount=amount,
            transaction_type='buy'
        )

        customer = Customer.objects.get(user_id=user_id)

        if customer.status == 'suspended':
            logger.warning(
                f"Buy blocked — account suspended | user_id={user_id} asset={asset}"
            )
            raise CustomerSuspended('حساب کاربری شما مسدود شده است و امکان انجام تراکنش وجود ندارد')

        pending_transaction = TransactionSelector.get_pending_transaction(
            customer=customer, currency=currency)
        if pending_transaction:
            logger.warning(
                f"Buy blocked — pending transaction exists | user_id={user_id} asset={asset}"
            )
            raise ActionDisabled(
                'شما یک درخواست در حال انتظار دارید. لطفا تا تکمیل آن صبر کنید.')

        DailyLimitService.check_daily_limit(customer, amount, 'buy')

        if buy_from_wallet:

            if not currency.buy_from_wallet:
                logger.warning(f"Buy blocked — wallet method disabled | user_id={user_id} asset={asset}")
                raise ActionDisabled('در حال حاضر امکان خرید از کیف پول وجود ندارد')

            customer_ip = get_client_ip(request)
            timestamp = get_date_time()['timestamp']

            with transaction.atomic():

                available_balance = CurrencyBalanceService.calculate_available_balance_for_update(
                    symbol=asset)
                if Decimal(calculated_price['data']['gold_amount']) > Decimal(str(available_balance)):
                    logger.warning(
                        f"Buy blocked — insufficient system balance | user_id={user_id} asset={asset} "
                        f"requested={calculated_price['data']['gold_amount']} available={available_balance}"
                    )
                    raise InsufficientSystemBalance('میزان درخواستی بیشتر از موجودی فعلی است')

                user_wallet_balance = WalletSelector.get_user_balance_for_update(
                    user_id=user_id, wallet_type='irt'
                )

                if int(calculated_price['data']['total_amount']) > int(user_wallet_balance):
                    logger.warning(
                        f"Buy blocked — insufficient user balance | user_id={user_id} "
                        f"required={calculated_price['data']['total_amount']} balance={user_wallet_balance}"
                    )
                    raise InsufficientUserBalance('موجودی کیف پول ناکافی است')

                wallet_entry = WalletService.create_wallet_entry(
                    customer=customer,
                    wallet_type='irt',
                    amount=calculated_price['data']['total_amount'] * -1,
                    desc=f'بابت خرید {currency.fa_title}',
                    ip=customer_ip,
                    timestamp=timestamp
                )

                TransactionService.create_buy_transaction(
                    customer=customer,
                    currency=currency,
                    wallet=wallet_entry,
                    deposit_method='wallet',
                    calculated_price=calculated_price,
                    ip=customer_ip,
                    timestamp=timestamp
                )

            logger.info(
                f"Buy order registered (wallet) | user_id={user_id} asset={asset} "
                f"gold={calculated_price['data']['gold_amount']}g "
                f"total={calculated_price['data']['total_amount']}IRT"
            )
            return {'message': 'درخواست خرید با موفقیت ثبت شد'}

        if not buy_from_wallet:

            if not currency.buy_from_gateway:
                logger.warning(f"Buy blocked — gateway method disabled | user_id={user_id} asset={asset}")
                raise ActionDisabled('در حال حاضر امکان خرید از درگاه وجود ندارد')

            card_exists = BankCardSelectors.check_user_has_bank_card(user_id=user_id)
            if not card_exists:
                logger.warning(
                    f"Buy blocked — no verified bank card | user_id={user_id} asset={asset}"
                )
                raise VerifiedBankCardNotFound(
                    'برای اتصال به درگاه میبایست کارت بانکی شما ثبت و تایید شده باشد'
                )

            total_amount = int(calculated_price['data']['total_amount'])
            unit_price = int(calculated_price['data']['price_per_gram'])

            with transaction.atomic():
                invoice = PaymentService.create_invoice(
                    customer=customer,
                    total_price=total_amount,
                    invoice_type='buy',
                    unit_price=unit_price,
                    fee=calculated_price['data']['fee_toman'],
                    maintenance_fee=calculated_price['data']['maintenance_fee'],
                )

            try:
                payment_data = PaymentService.create_payment_gateway_link(
                    amount=total_amount,
                    invoice_id=invoice.id
                )
            except Exception as e:
                logger.error(
                    f"Gateway link creation FAILED | user_id={user_id} asset={asset} "
                    f"invoice_id={invoice.id} error={e}"
                )
                invoice.gateway_response = "gateway_failed"
                invoice.status = "failed"
                invoice.save(update_fields=["gateway_response", "status"])
                raise

            authority = payment_data['authority']
            payment_link = payment_data['payment_link']

            invoice.payment_gateway = 'zari'
            invoice.gateway_track_id = authority
            invoice.save(update_fields=['payment_gateway', 'gateway_track_id'])

            logger.info(
                f"Buy order gateway invoice created | user_id={user_id} asset={asset} "
                f"invoice_id={invoice.id} amount={total_amount}IRT authority={authority}"
            )
            return {'message': payment_link}
        
    @staticmethod
    def sell_asset(request, asset: str, amount: Decimal, card_withdaraw: bool, bank_card_id: int = None) -> dict:
        """
        Submit a sell order for a gold-based asset on behalf of the authenticated user.

        This method handles the full validation and preparation workflow prior
        to creating a pending sell transaction. If the sale is performed directly
        into the wallet (not via bank withdrawal), the user's gold balance is
        locked and deducted inside an atomic operation, and a matching wallet
        entry and transaction record are created.

        Main responsibilities:
        - Validate site-level and currency-level sell availability.
        - Calculate the sell price using PriceService.
        - Ensure the user has no pending transactions for the same currency.
        - Validate daily sell limits based on the resulting IRT amount.
        - For wallet-based settlement:
            * Lock and validate user's gold (XAU) balance.
            * Create a gold wallet debit entry.
            * Create the corresponding pending sell transaction.
            * Execute all operations inside an atomic DB transaction to maintain
              ledger consistency.

        Parameters:
            request (HttpRequest):
                The authenticated user's request instance.
            asset (str):
                Currency symbol to sell (e.g., "XAU18").
            amount (Decimal):
                Gold amount to be sold.
            card_withdaraw (bool):
                If False, the sale is settled to the user's wallet.
                If True, settlement is via bank withdrawal.
            bank_card_id (int, optional):
                The user's bank card ID when using withdrawal-to-card.

        Returns:
            dict:
                A success message confirming the sell request submission.

        Raises:
            CurrencyNotBuyable:
                If site or currency does not allow selling.
            ActionDisabled:
                If the user already has a pending transaction for this currency.
            InsufficientUserBalance:
                If the user does not have enough gold balance to complete the sale.
            ValidationError:
                For invalid input or limit violations.
        """

        user_id = request.user.id
        logger.info(
            f"Sell request initiated | user_id={user_id} asset={asset} "
            f"amount={amount}g withdraw={'bank' if card_withdaraw else 'wallet'}"
        )

        site_settings = get_site_settings()
        if not site_settings.is_sell:
            logger.warning(f"Sell blocked — globally disabled | user_id={user_id} asset={asset}")
            raise CurrencyNotBuyable("در حال حاضر امکان فروش وجود ندارد")

        currency = CurrencySelector.get_currency_by_symbol(symbol=asset)
        if not currency.is_sell:
            logger.warning(f"Sell blocked — currency disabled | user_id={user_id} asset={asset}")
            raise CurrencyNotBuyable("در حال حاضر امکان فروش وجود ندارد")

        calculated_price = PriceService.calculate_xau18_currency_price(
            unit='XAU18',
            amount=amount,
            transaction_type='sell'
        )

        customer = Customer.objects.get(user_id=user_id)

        if customer.status == 'suspended':
            logger.warning(
                f"Sell blocked — account suspended | user_id={user_id} asset={asset}"
            )
            raise CustomerSuspended('حساب کاربری شما مسدود شده است و امکان انجام تراکنش وجود ندارد')

        pending_transaction = TransactionSelector.get_pending_transaction(
            customer=customer, currency=currency)
        if pending_transaction:
            logger.warning(
                f"Sell blocked — pending transaction exists | user_id={user_id} asset={asset}"
            )
            raise ActionDisabled('شما یک درخواست در حال انتظار دارید. لطفا تا تکمیل آن صبر کنید')

        DailyLimitService.check_daily_limit(
            customer, calculated_price['data']['total_amount'], 'sell')

        withdraw_method = 'wallet'
        customer_ip = get_client_ip(request)
        timestamp = get_date_time()['timestamp']

        with transaction.atomic():

            user_wallet_balance = WalletSelector.get_user_balance_for_update(
                user_id=user_id, wallet_type='xau'
            )

            if Decimal(calculated_price['data']['gold_amount']) > Decimal(str(user_wallet_balance)):
                logger.warning(
                    f"Sell blocked — insufficient XAU balance | user_id={user_id} "
                    f"required={calculated_price['data']['gold_amount']}g balance={user_wallet_balance}g"
                )
                raise InsufficientUserBalance('موجودی صندوق طلا ناکافی است')

            if card_withdaraw:
                card = BankCardSelectors.get_customer_card_by_id(
                    card_id=bank_card_id,
                    customer_id=customer.id
                )
                withdraw_method = 'bank'

            wallet_entry = WalletService.create_wallet_entry(
                customer=customer,
                wallet_type='xau',
                amount=Decimal(calculated_price['data']['gold_amount']) * -1,
                desc=f'بابت فروش {currency.fa_title}',
                ip=customer_ip,
                timestamp=timestamp
            )

            TransactionService.create_sell_transaction(
                customer=customer,
                currency=currency,
                wallet=wallet_entry,
                card=card if withdraw_method == 'bank' else None,
                withdraw_method=withdraw_method,
                calculated_price=calculated_price,
                ip=customer_ip,
                timestamp=timestamp
            )

        logger.info(
            f"Sell order registered | user_id={user_id} asset={asset} "
            f"gold={calculated_price['data']['gold_amount']}g "
            f"total={calculated_price['data']['total_amount']}IRT withdraw={withdraw_method}"
        )
        return {'message': 'درخواست فروش با موفقیت ثبت شد'}
    