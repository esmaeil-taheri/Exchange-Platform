from django.db import transaction

from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.customers.models.customer import Customer
from apps.customers.exceptions.customer_exceptions import CustomerSuspended
from apps.customers.selectors.bank_card_selectors import BankCardSelectors
from apps.exchange.exceptions.exchange_exceptions import InsufficientUserBalance
from apps.exchange.services.wallet_service import WalletService
from apps.core.utils.date_time_utils import get_date_time
from apps.core.utils.security_utils import get_client_ip
from apps.settlements.tasks.settlement_tasks import process_withdrawal_requests
from apps.core.models.idempotency import IdempotencyRecord
from apps.core.services.idempotency import IdempotencyService
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


class SettlementService:

    @staticmethod
    def create_withdrawal_request(customer, card, amount, method, remaining_wallet_amount):
        return Withdrawal.objects.create(
            customer=customer,
            card=card,
            amount=amount,
            settlement_method=method,
            remaining_wallet_amount=remaining_wallet_amount,
        )

    @staticmethod
    def initiate_withdrawal_request(
        amount, card_id, request, idempotency_key: str | None = None
    ):
        user_id = request.user.id
        logger.info(
            f"Withdrawal request initiated | user_id={user_id} amount={amount}IRT card_id={card_id}"
        )

        customer_ip = get_client_ip(request)
        timestamp = get_date_time()['timestamp']

        with transaction.atomic():
            # Idempotency claim before the customer lock — the same ordering
            # every financial endpoint uses, so two requests sharing a key can
            # never queue on these two locks in opposite orders. The claim
            # commits with the debit below, so a duplicate that arrives after
            # this transaction replays instead of withdrawing twice.
            guard = IdempotencyService.acquire(
                user_id=user_id,
                endpoint=IdempotencyRecord.Endpoint.WITHDRAW,
                key=idempotency_key,
                params={'amount': amount, 'card_id': card_id},
            )
            if guard.replayed:
                logger.info(
                    f"Withdrawal replayed from idempotency key | user_id={user_id} "
                    f"reference={guard.record.reference or '-'}"
                )
                return guard.response

            # Customer row lock (same ordering as ExchangeService) so a
            # concurrent buy/sell/withdrawal of this customer cannot interleave
            # between the balance check and the wallet debit below.
            customer = Customer.objects.select_for_update().get(user_id=user_id)

            # Checked inside the lock, not just at the permission layer: an admin
            # suspending the account mid-request must not be able to interleave
            # between the permission check and the wallet debit below.
            if customer.status == 'suspended':
                logger.warning(
                    f"Withdrawal blocked — account suspended | user_id={user_id} "
                    f"amount={amount}IRT card_id={card_id}"
                )
                raise CustomerSuspended(
                    'حساب کاربری شما مسدود شده است و امکان انجام تراکنش وجود ندارد'
                )

            card = BankCardSelectors.get_customer_card_by_id(
                card_id=card_id, customer_id=customer.id
            )

            user_wallet_balance = WalletSelector.get_user_balance_under_customer_lock(
                user_id=user_id, wallet_type='irt'
            )

            if amount > int(user_wallet_balance):
                logger.warning(
                    f"Withdrawal blocked — insufficient balance | user_id={user_id} "
                    f"requested={amount}IRT balance={user_wallet_balance}IRT"
                )
                raise InsufficientUserBalance('موجودی کیف پول ناکافی است')

            withdrawal = SettlementService.create_withdrawal_request(
                customer=customer,
                card=card,
                amount=amount,
                method='پایا',
                remaining_wallet_amount=user_wallet_balance - amount
            )

            WalletService.create_wallet_entry(
                customer=customer,
                wallet_type='irt',
                amount=amount * -1,
                desc=f'بابت درخواست برداشت به شماره: {withdrawal.id}',
                ip=customer_ip,
                timestamp=timestamp
            )

            guard.complete(
                {"message": "درخواست برداشت با موفقیت ثبت شد"},
                reference=f'withdrawal:{withdrawal.id}',
            )

        logger.info(
            f"Withdrawal created — IRT debited | user_id={user_id} "
            f"withdrawal_id={withdrawal.id} amount={amount}IRT remaining={user_wallet_balance - amount}IRT"
        )

        try:
            process_withdrawal_requests.apply_async(
                args=[withdrawal.id],
                countdown=10
            )
            logger.info(
                f"Withdrawal task queued | withdrawal_id={withdrawal.id} user_id={user_id}"
            )
            return {"message": "درخواست برداشت با موفقیت ثبت شد"}

        except Exception as e:
            logger.error(
                f"Failed to queue withdrawal task | withdrawal_id={withdrawal.id} "
                f"user_id={user_id} error={e}"
            )
            return {"message": "درخواست برداشت با موفقیت ثبت شد"}
