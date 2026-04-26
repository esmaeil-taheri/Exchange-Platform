from apps.exchange.models.currency_balance import CurrencyBalance


class CurrencyBalanceSelector:

    @staticmethod
    def get_currency_balance_by_symbol(symbol: str):
        return CurrencyBalance.objects.get(currency__symbol=symbol)
    
    @staticmethod   
    def get_active_balance_for_update_by_symbol(symbol: str):
        return CurrencyBalance.objects.select_for_update().get(
            currency__symbol=symbol).active_balance
