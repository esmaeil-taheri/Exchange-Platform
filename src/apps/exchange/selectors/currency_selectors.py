from apps.exchange.models.currency import Currency
from src.apps.exchange.exceptions.currency_exceptions import CurrencyNotFound

class CurrencySelector:

    @staticmethod
    def get_currency_by_symbol(symbol: str):
        try:
            return Currency.objects.get(symbol=symbol)
        except Currency.DoesNotExist:
            raise CurrencyNotFound('رمز ارز یافت نشد')
