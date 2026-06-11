from django.conf import settings

from apps.core.services.payment.base import PaymentGateway
from apps.core.exceptions.base import PaymentGatewayError

import logging

import requests

logger = logging.getLogger(__name__)


class ZarinpalGateway(PaymentGateway):

    def __init__(self):
        self.merchant_key = settings.ZARINPAL_MERCHANT_KEY

    @staticmethod
    def _server_name() -> str:
        return 'sandbox' if settings.DEBUG else 'payment'

    def process_payment(self, amount: int, invoice_id: int) -> dict:
        payload = {
            'merchant_id': self.merchant_key,
            'currency': 'IRT',
            'amount': amount,
            'description': 'Buy',
            'callback_url': settings.ZARINPAL_CALLBACK_URL,
            'order_id': str(invoice_id)
        }

        server_name = self._server_name()

        try:
            response = requests.post(
                f'https://{server_name}.zarinpal.com/pg/v4/payment/request.json',
                json=payload,
                timeout=7
            )
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"[zarinpal] payment request failed | invoice_id={invoice_id} error={e}")
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')

        data_block = data.get('data') or {}
        authority = data_block.get('authority') if isinstance(data_block, dict) else None

        if data.get('errors') or not authority:
            logger.error(
                f"[zarinpal] payment request rejected | invoice_id={invoice_id} "
                f"errors={data.get('errors')}"
            )
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')

        return {
            "authority": authority,
            "payment_link": f"https://{server_name}.zarinpal.com/pg/StartPay/{authority}"
        }

    def verify_payment(self, authority: str, amount: int):
        """
        Verify a payment with Zarinpal.

        Returns:
            dict: full gateway response when the payment is verified (code 100).
            101:  payment was already verified before.
            102:  payment failed, was rejected, or the gateway returned an
                  unexpected code — caller must treat it as not paid.

        Raises:
            PaymentGatewayError: on connection failure or unparsable response.
        """
        payload = {
            'merchant_id': self.merchant_key,
            'authority': authority,
            'amount': amount,
        }

        server_name = self._server_name()

        try:
            response = requests.post(
                f"https://{server_name}.zarinpal.com/pg/v4/payment/verify.json",
                json=payload,
                timeout=7
            )
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"[zarinpal] verify request failed | authority={authority} error={e}")
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')

        if data.get('errors'):
            return 102

        data_block = data.get('data') or {}
        code = data_block.get('code') if isinstance(data_block, dict) else None

        if code == 100:
            return data

        if code == 101:
            return 101

        logger.warning(
            f"[zarinpal] verify returned unexpected code | authority={authority} code={code}"
        )
        return 102
