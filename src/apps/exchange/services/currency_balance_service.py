from apps.exchange.selectors.currency_balance_selectors import CurrencyBalanceSelector
from apps.exchange.selectors.transaction_selectors import TransactionSelector


class CurrencyBalanceSerivce:

    @staticmethod
    def calculate_available_balance(symbol: str):
        currency_balance = CurrencyBalanceSelector.get_currency_balance_by_symbol(symbol=symbol)
        active_balance = currency_balance.active_balance
        pending_balance = TransactionSelector.get_pending_transactions_amount(symbol=symbol)
        return round(active_balance - pending_balance, 4)