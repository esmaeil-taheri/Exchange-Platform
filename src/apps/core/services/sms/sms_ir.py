import requests

from django.conf import settings

from apps.core.services.sms.base import BaseSmsProvider


class SmsIrProvider(BaseSmsProvider):
    def __init__(self):
        self._url = "https://api.sms.ir/v1/send/verify"
        self._api_key = settings.SMS_IR_API_KEY

    def send_otp(self, code: str, phone_number: str) -> dict:
        body = {
            "mobile": phone_number,
            "templateId": settings.SEND_LOGIN_OTP_TEMPLATE_ID,
            "parameters": [
                {
                    "name": "Code",
                    "value": code
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self._api_key,
        }

        response = requests.post(
            self._url,
            json=body,
            headers=headers,
            timeout=10
        )
        
        result = response.json()

        if response.status_code != 200:
            return {
                "code": 101,
                "message": response["message"]
            }

        
        if result["status"] == 1:
            return {
                "code": 100,
                "message": "success"
            }
        else:
            return {
                "code": 102,
                "message": response["message"]
            }
    
    def send_message(self, message: str, phone_number: str):

        payload = {
            "mobile": phone_number,
            "templateId": settings.SEND_MESSAGE_TEMPLATE_ID,
            "parameters": [
                {"name": "message", "value": str(message)},
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "x-api-key": self._api_key,
        }

        response = requests.post(
            self._url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        result = response.json()

        if response.status_code != 200:
            return {
                "code": 101,
                "message": response["message"]
            }

        
        if result["status"] == 1:
            return {
                "code": 100,
                "message": "success"
            }
        else:
            return {
                "code": 102,
                "message": response["message"]
            }
    