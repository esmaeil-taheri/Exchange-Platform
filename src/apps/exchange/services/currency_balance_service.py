from apps.exchange.selectors.currency_balance_selectors import CurrencyBalanceSelector
from apps.exchange.selectors.transaction_selectors import TransactionSelector


class CurrencyBalanceSerivce:

    @staticmethod
    def calculate_available_balance_for_update(symbol: str):
        active_balance = CurrencyBalanceSelector.get_active_balance_for_update_by_symbol(symbol=symbol)
        pending_balance = TransactionSelector.get_pending_transactions_amount_for_update(symbol=symbol)
        return round(active_balance - pending_balance, 4)