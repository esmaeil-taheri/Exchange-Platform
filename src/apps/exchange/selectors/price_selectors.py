from apps.exchange.models.price_log import CurrencyPriceLog

from collections import defaultdict
from django.utils import timezone
from datetime import timedelta

import time


class PriceSelector:

    @staticmethod
    def get_xau18_quarter_hourly_chart_data(symbol='XAU18') -> dict:
        """
        Generate chart data every 15 minutes for the last 24 hours
        """
        now = timezone.now()
        start_time = now - timedelta(hours=24)
        
        end_timestamp = 1776748500
        start_timestamp = 1776662100

        # end_timestamp = int(now.timestamp())
        # start_timestamp = int(start_time.timestamp())
        
        # Single query to get all data
        price_logs = CurrencyPriceLog.objects.filter(
            currency__symbol=symbol,
            timestamp__gte=start_timestamp,
            timestamp__lte=end_timestamp
        ).values('timestamp', 'price').order_by('timestamp')

        print(len(price_logs))
        
        if not price_logs:
            return {
                "message": "No data available",
                "data": None
            }
        
        # Group by 15-minute intervals (900 seconds)
        interval_data = defaultdict(list)
        for log in price_logs:
            interval_bucket = (log['timestamp'] // 900) * 900
            interval_data[interval_bucket].append(log['price'])
        
        # Build chart data - 96 intervals in 24 hours (24 * 4)
        chart_data = []
        for i in range(96):
            interval_start = start_timestamp + (i * 900)
            if interval_start in interval_data:
                # Get last price of the interval
                last_price = interval_data[interval_start][-1]
                chart_data.append([interval_start, last_price])
        
        if not chart_data:
            return {
                "message": "No data available",
                "data": None
            }
        
        prices = [item[1] for item in chart_data]
        min_price = min(prices)
        max_price = max(prices)
        
        first_price = chart_data[0][1]
        last_price = chart_data[-1][1]
        percentage_change = round(((last_price - first_price) / first_price) * 100, 2)
        
        return {
            "message": "Success",
            "data": {
                "Chart_data": {
                    "chart_data": chart_data,
                    "min_price": min_price,
                    "max_price": max_price,
                    "last_percentage_change": percentage_change
                }
            }
        }

    @staticmethod
    def get_xau18_current_price(symbol='XAU18') -> dict:
        price_log = CurrencyPriceLog.objects.select_related('currency').filter(
            currency__symbol=symbol
        ).order_by('-id').first()

        return {
            'price': price_log.price if price_log else 0,
            'timestamp': int(price_log.timestamp)
        }

    @staticmethod
    def get_xau18_buy_sell_price(symbol='XAU18') -> dict:
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