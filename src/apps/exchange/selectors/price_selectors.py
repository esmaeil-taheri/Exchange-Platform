from apps.exchange.models.price_log import CurrencyPriceLog

import time


class PriceSelector:

    @staticmethod
    def get_buy_sell_price(symbol='XAU18') -> dict:
        price_logs = (
            CurrencyPriceLog.objects
            .select_related('currency')
            .filter(currency__symbol=symbol)
            .order_by('-id')[:2]
        )

        if len(price_logs) == 1:
            last = price_logs[0]
            prev = None
        else:
            last, prev = price_logs[0], price_logs[1]

        difference_buy = (last.price - prev.price) if prev else 0
        difference_sell = (last.price - prev.price) if prev else 0

        currency = last.currency

        lowest_buy = currency.lowest_amount_buy
        lowest_sell = currency.lowest_amount_sell

        buy_sell_fee = currency.fixed_buy_fee_toman

        buy_fee = buy_sell_fee + int((currency.maintance_fee * lowest_buy))
        lower_buy_price = int(last.price * lowest_buy) + buy_fee

        lower_sell_price = int(last.price * lowest_sell) - buy_sell_fee

        response = {
            "price_buy": last.price,
            "price_sell": last.price,
            "difference_price_buy": difference_buy,
            "difference_price_sell": difference_sell,
            "lower_amounts": {
                "buy_toman": lower_buy_price,
                "sell_toman": lower_sell_price,
                "buy_gold": round(lowest_buy, 4),
                "sell_gold": round(lowest_sell, 4),
            },
            "system_balance_amount": "10000",
            "timestamp": int(time.time()),
        }

        return response
