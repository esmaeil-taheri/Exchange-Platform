

from apps.exchange.selectors.daily_limit_selectors import DailyLimitSelector
from apps.exchange.exceptions.daily_limit_exceptions import DailyLimitExceeded


class DailyLimitService:

    @staticmethod
    def check_daily_limit(customer, amount, transaction_type):

        base_limit_obj = DailyLimitSelector.get_base_daily_limit()

        if transaction_type == "buy":
            base_limit = base_limit_obj.buy_amount
        else:
            base_limit = base_limit_obj.sell_amount

        print(base_limit)

        additional_limit = DailyLimitSelector.get_approved_limit_increases(
            customer,
            transaction_type
        )

        print(additional_limit)

        today_usage = DailyLimitSelector.get_customer_daily_usage(
            customer,
            transaction_type
        )

        print(today_usage)

        final_limit = base_limit + additional_limit

        print(final_limit)

        if today_usage + amount > final_limit:
            raise DailyLimitExceeded(
                "مقدار خرید بیشتر از سقف مجاز روزانه شماست"
            )
        