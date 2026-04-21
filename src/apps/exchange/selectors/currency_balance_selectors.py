from apps.exchange.models.currency_balance import CurrencyBalance


class CurrencyBalanceSelector:

    @staticmethod
    def get_currency_balance_by_symbol(symbol: str):
        return CurrencyBalance.objects.get(currency__symbol=symbol)

