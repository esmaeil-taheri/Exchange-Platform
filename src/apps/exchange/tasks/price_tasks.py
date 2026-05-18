import logging

import requests
from celery import shared_task

from apps.exchange.models.currency import Currency
from apps.exchange.models.price_log import CurrencyPriceLog
from apps.core.utils.date_time_utils import get_date_time

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fetch_gold_price(self):
    url = "https://melligold.com/api/v1/exchange/buy-sell-price/?symbol=XAU18&format=json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        logger.error("[task=fetch_gold_price] Request timed out")
        raise self.retry(exc=None, countdown=30 * (self.request.retries + 1))

    except requests.exceptions.ConnectionError as e:
        logger.error(f"[task=fetch_gold_price] Connection error | error={e}")
        raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

    except requests.exceptions.HTTPError as e:
        logger.error(f"[task=fetch_gold_price] HTTP error | status={e.response.status_code} error={e}")
        raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

    except ValueError as e:
        logger.error(f"[task=fetch_gold_price] Invalid JSON response | error={e}")
        return "Cannot parse gold price response"

    try:
        price = data['data']['price_buy']
    except (KeyError, TypeError) as e:
        logger.error(f"[task=fetch_gold_price] Unexpected response structure | error={e} data={data}")
        return "Unexpected response structure"

    if not price or int(price) <= 0:
        logger.error(f"[task=fetch_gold_price] Invalid price value | price={price}")
        return "Invalid price value received"

    try:
        currency = Currency.objects.get(symbol='XAU18')
    except Currency.DoesNotExist:
        logger.error("[task=fetch_gold_price] XAU18 currency not found in database")
        return "Currency XAU18 not found"

    CurrencyPriceLog.objects.create(
        currency=currency,
        price=price,
        timestamp=get_date_time()['timestamp']
    )

    logger.info(f"[task=fetch_gold_price] Price updated | price={price}")
    return "Gold price fetched successfully"