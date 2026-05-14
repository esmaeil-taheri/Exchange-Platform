from django.db import transaction

from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.customers.models.customer import Customer
from apps.customers.selectors.bank_card_selectors import BankCardSelectors
from apps.exchange.exceptions.exchange_exceptions import InsufficientUserBalance
from apps.exchange.services.wallet_service import WalletService
from apps.core.utils.date_time_utils import get_date_time
from apps.core.utils.security_utils import get_client_ip


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
    def initiate_withdrawal_request(amount, card_id, request):

        customer = Customer.objects.get(user_id=request.user.id)
        card = BankCardSelectors.get_customer_card_by_id(
            card_id=card_id, customer_id=customer.id
        )

        customer_ip = get_client_ip(request)
        timestamp = get_date_time()['timestamp']
        
        with transaction.atomic():
            user_wallet_balance = WalletSelector.get_user_balance_for_update(
                user_id=request.user.id, wallet_type='irt'
            )

            if amount > int(user_wallet_balance):
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

            return {"message": "درخواست برداشت با موفقیت ثبت شد"}