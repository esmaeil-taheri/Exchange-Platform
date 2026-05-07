from celery import shared_task

from apps.exchange.models.price_log import CurrencyPriceLog
from apps.exchange.models.currency import Currency
from apps.core.utils.date_time_utils import get_date_time

import requests

@shared_task(bind=True)
def fetch_gold_price(self):
    url = "https://melligold.com/api/v1/exchange/buy-sell-price/?symbol=XAU18&format=json"

    try:
        response = requests.get(url, timeout=10).json()

        currency = Currency.objects.get(symbol='XAU18')

        CurrencyPriceLog.objects.create(
            currency=currency,
            price=response['data']['price_buy'],
            timestamp=get_date_time()['timestamp']
        )
        
        return 'Gold price fetched successfully'

    except:
        return 'Cannot fetch gold price'