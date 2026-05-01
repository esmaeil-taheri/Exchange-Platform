from decimal import Decimal
from django.db import transaction

from apps.customers.models.customer import Customer
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.exchange.exceptions.currency_exceptions import CurrencyNotBuyable
from apps.exchange.exceptions.exchange_exceptions import InsufficientSystemBalance, InsufficientUserBalance
from apps.exchange.services.daily_limit_services import DailyLimitService
from apps.exchange.services.currency_balance_service import CurrencyBalanceSerivce
from apps.exchange.selectors.currency_selectors import CurrencySelector
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.core.exceptions.base import ActionDisabled
from apps.core.utils.date_time_utils import get_date_time
from apps.core.utils.security_utils import get_client_ip
from apps.exchange.services.transaction_service import TransactionService
from apps.exchange.services.wallet_service import WalletService

from .price_services import PriceService


class ExchangeService:

    @staticmethod
    def buy_asset(request, asset: str, amount: int, buy_from_wallet: bool) -> dict:

        site_settings = get_site_settings()
        if not site_settings.is_buy:
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        currency = CurrencySelector.get_currency_by_symbol(symbol=asset)
        if not currency.is_buy:
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        calculated_price = PriceService.calculate_xau18_currency_price(
            unit='IRT',
            amount=amount,
            transaction_type='buy'
        )

        customer = Customer.objects.get(user_id=request.user.id)

        DailyLimitService.check_daily_limit(customer, amount, 'buy')

        if buy_from_wallet:

            if not currency.buy_from_wallet:
                raise ActionDisabled('در حال حاضر امکان خرید از کیف پول وجود ندارد')
            
            customer_ip = get_client_ip(request)
            timestamp = get_date_time()['timestamp']

            with transaction.atomic():

                available_balance = CurrencyBalanceSerivce.calculate_available_balance_for_update(symbol=asset)
                if Decimal(calculated_price['data']['gold_amount']) > Decimal(str(available_balance)):
                    raise InsufficientSystemBalance('میزان درخواستی بیشتر از موجودی فعلی است')

                user_wallet_balance = WalletSelector.get_user_balance_for_update(
                    user_id=request.user.id, wallet_type='irt'
                )

                if int(calculated_price['data']['total_amount']) > int(user_wallet_balance):
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
                    calculated_price=calculated_price,
                    ip=customer_ip,
                    timestamp=timestamp
                )

            return {'message': 'خرید با موفقیت انجام شد'}
        
        else:
            pass
    
    @staticmethod
    def sell_asset(request, asset: str, amount: Decimal, card_withdaraw: bool, bank_card_id: int = None) -> dict:

        site_settings = get_site_settings()
        if not site_settings.is_sell:
            raise CurrencyNotBuyable("در حال حاضر امکان فروش وجود ندارد")
        
        currency = CurrencySelector.get_currency_by_symbol(symbol=asset)
        if not currency.is_sell:
            raise CurrencyNotBuyable("در حال حاضر امکان فروش وجود ندارد")
        
        calculated_price = PriceService.calculate_xau18_currency_price(
            unit='XAU18',
            amount=amount,
            transaction_type='sell'
        )

        customer = Customer.objects.get(user_id=request.user.id)

        DailyLimitService.check_daily_limit(customer, calculated_price['data']['total_amount'], 'sell')

        if not card_withdaraw:
            
            customer_ip = get_client_ip(request)
            timestamp = get_date_time()['timestamp']

            with transaction.atomic():

                user_wallet_balance = WalletSelector.get_user_balance_for_update(
                    user_id=request.user.id, wallet_type='xau'
                )

                if Decimal(calculated_price['data']['gold_amount']) > Decimal(str(user_wallet_balance)):
                    raise InsufficientUserBalance('موجودی صندوق طلا ناکافی است')

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
                    calculated_price=calculated_price,
                    ip=customer_ip,
                    timestamp=timestamp
                )

            return {'message': 'فروش با موفقیت انجام شد'}
    
        else:
            pass
