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
            # NOTE: For testing purposes, we are skipping the actual API call to Zarinpal and returning a mock response.

            if not settings.DEBUG:

                response = requests.post(
                    f'https://{server_name}.zarinpal.com/pg/v4/payment/request.json', 
                    json=payload,
                    timeout=7
                )
            
                data = response.json()

            data = {'data': {'authority': 'S000000000000000000000000000000xzq52', 'fee': 150000, 'fee_type': 'Merchant', 'code': 100, 'message': 'Success'}, 'errors': []}

            return {
                "authority": data['data']['authority'], 
                "payment_link": f"https://{server_name}.zarinpal.com/pg/StartPay/{data['data']['authority']}"
            }
        except Exception:
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')

    def verify_payment(self, authority: str, amount: int) -> dict:
        payload = {
            'merchant_id': self.merchant_key,
            'authority': authority,
            'amount': amount,
        }

        server_name = 'payment'

        if settings.DEBUG:
            server_name = 'sandbox'

        try:
            # NOTE: For testing purposes, we are skipping the actual API call to Zarinpal and returning a mock response.

            if not settings.DEBUG:
            
                response = requests.post(
                    f"https://{server_name}.zarinpal.com/pg/v4/payment/verify.json",
                    json=payload,
                    timeout=7
                )

                data = response.json()

            data = {"data": {"code": 100, "message": "Verified", "card_hash": "1EBE3EBEBE35C7EC0F8D6EE4F2F859107A87822CA179BC9528767EA7B5489B69","card_pan": "621986******3905", "ref_id": 201, "fee_type": "Merchant","fee": 0},"errors": []}

            errors = data.get('errors')
            if errors:
                return 102
            
            elif data['data']['code'] == 100:
                return data
            
            elif data['data']['code'] == 101:
                return 101
        except:
            raise PaymentGatewayError('خطا در اتصال با درگاه پرداخت')