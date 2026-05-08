from django.conf import settings

from apps.core.services.payment.base import PaymentGateway
from apps.core.exceptions.base import PaymentGatewayError

import requests


class ZarinpalGateway(PaymentGateway):

    def __init__(self):
        self.merchant_key = settings.ZARINPAL_MERCHANT_KEY

    def process_payment(self, amount: int, invoice_id: int) -> dict:
        payload = {
            'merchant_id': self.merchant_key,
            'currency': 'IRT',
            'amount': amount,
            'description': 'Buy',
            'callback_url': settings.ZARINPAL_CALLBACK_URL,
            'order_id': str(invoice_id)
        }

        server_name = 'payment'

        if settings.DEBUG:
            server_name = 'sandbox'

        try: 
            response = requests.post(
                f'https://{server_name}.zarinpal.com/pg/v4/payment/request.json', 
                json=payload,
                timeout=7
            )
        
            data = response.json()

            return {
                "authority": data['data']['authority'], 
                "payment_link": f"https://{server_name}.zarinpal.com/pg/StartPay/{data['data']['authority']}"
            }
        except Exception:
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')

                                                                              