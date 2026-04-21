from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.exchange.exceptions.currency_exceptions import CurrencyNotBuyable
from apps.exchange.services.daily_limit_services import DailyLimitService
from apps.exchange.selectors.currency_selectors import CurrencySelector
from apps.customers.models.customer import Customer

from .price_services import PriceService


class ExchangeService:

    @staticmethod
    def buy_asset(user_id: int, asset: str, amount: int, buy_from_wallet: bool) -> dict:

        site_settings = get_site_settings()
        if not site_settings.is_buy:
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        currency = CurrencySelector.get_currency_by_symbol(symbol=asset)
        if not currency.is_buy:
            raise CurrencyNotBuyable("در حال حاضر امکان خرید وجود ندارد")

        calculated_price = PriceService.calculate_xau18_currency_price(
            unit='IRT',
            amount=amount,
            transaction_type='buy'
        )

        customer = Customer.objects.get(user_id=user_id)

        DailyLimitService.check_daily_limit(customer, amount, 'buy')
