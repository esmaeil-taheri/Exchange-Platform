from django.db.models import Sum

from apps.exchange.models.transaction import Transaction


class TransactionSelector:

    @staticmethod
    def get_pending_transactions_amount(symbol: str):
        """
        Sum the amounts of every pending transaction for one currency.

        Carried a `select_for_update()` that Django silently dropped, because
        `.aggregate()` does not carry the locking clause into the emitted SQL.
        Removed rather than made real: locking every pending row of a currency
        would serialize all trading system-wide and would deadlock against the
        settlement workers, which hold a single pending Transaction row while
        this path would be trying to lock the whole set.

        Serialization already comes from one level up. The only caller,
        `CurrencyBalanceService.calculate_available_balance_for_update`, holds a
        `FOR UPDATE` on the single `CurrencyBalance` row for this currency, so no
        two inventory checks can run at once. A worker moving a row out of
        `pending` concurrently can only raise the available balance, never lower
        it, so reading without a lock cannot oversell.
        """
        return Transaction.objects.filter(
            currency__symbol=symbol,
            status=Transaction.TRANSACTIONSTATUSES[0][0],
        ).aggregate(locked_balance=Sum('amount'))['locked_balance'] or 0

    @staticmethod
    def get_transactions_list_by_user_id(user_id: str):
        return Transaction.objects.filter(customer__user_id=user_id)
    
    @staticmethod
    def get_pending_transaction(customer, currency):
        return Transaction.objects.filter(
            customer=customer,
            currency=currency,
            status=Transaction.TRANSACTIONSTATUSES[0][0]
        ).first()