from apps.settlements.models.withdrawal import Withdrawal

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
