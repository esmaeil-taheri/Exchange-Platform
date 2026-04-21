from django.db.models import Sum

from apps.exchange.models.transaction import Transaction


class TransactionSelector:

    @staticmethod
    def get_pending_transactions_amount(symbol: str):
        return Transaction.objects.filter(
            currency__symbol=symbol,
            status=Transaction.TRANSACTIONSTATUSES[0][0],
        ).aggregate(locked_balance=Sum('amount'))['locked_balance'] or 0

    @staticmethod
    def get_transactions_list_by_user_id(user_id: str):
        return Transaction.objects.filter(customer__user_id=user_id)