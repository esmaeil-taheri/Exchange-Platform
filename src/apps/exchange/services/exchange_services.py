from decimal import Decimal
from django.db import transaction

from apps.customers.models.customer import Customer
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.exchange.exceptions.currency_exceptions import CurrencyNotBuyable
from apps.exchange.exceptions.exchange_exceptions import InsufficientSystemBalance, InsufficientUserBalance
from apps.exchange.services.daily_limit_services import DailyLimitService
from apps.exchange.services.currency_balance_service import CurrencyBalanceSerivce
from apps.exchange.selectors.currency_selectors import CurrencySelector
from apps.exchange.selectors.wallet_selectors import WalletSelector

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

        available_balance = CurrencyBalanceSerivce.calculate_available_balance(symbol=asset)

        print(calculated_price['data']['gold_amount'], available_balance)
        if Decimal(calculated_price['data']['gold_amount']) > Decimal(str(available_balance)):
            raise InsufficientSystemBalance('میزان درخواستی بیشتر از موجودی فعلی است')

        customer = Customer.objects.get(user_id=user_id)

        DailyLimitService.check_daily_limit(customer, amount, 'buy')

        if buy_from_wallet:

            irt_amount = WalletSelector.get_user_balance(user_id=user_id)['irt']['balance']
            if amount > irt_amount:
                raise InsufficientUserBalance('مبلغ فاکتور شما بیشتر از موجودی کیف پول است')

            with transaction.atomic:
                pass
