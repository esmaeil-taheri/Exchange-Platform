import uuid
import logging

import requests

from django.conf import settings

from apps.core.exceptions.inquiry_exceptions import InquiryServiceError

logger = logging.getLogger(__name__)


class InquiryService:
    """
    Client for the NeginHub KYC inquiry API.

    Contract:
        - Methods return the service's logical answer: a bool for match checks,
          the full response dict for data lookups, or None when the lookup was
          handled but found no valid result (e.g. wrong identity input).
        - InquiryServiceError is raised only for real failures: network errors,
          authentication problems, or malformed responses. A raised error must
          never be interpreted as "no match" by callers.
    """

    def __init__(self):
        self.base_url = 'https://api.neginhub.com/'
        self.username = settings.INQUIRY_SERVICE_USERNAME
        self.password = settings.INQUIRY_SERVICE_PASSWORD

    def _get_token(self) -> str:
        payload = {
            'grant_type': 'password',
            'Username': self.username,
            'Password': self.password,
        }

        try:
            response = requests.post(
                f'{self.base_url}api/v5/Authentication/GetToken',
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=20
            )
            data = response.json()
            token = (data.get('data') or {}).get('access_token')
        except (requests.RequestException, ValueError, AttributeError) as e:
            logger.error(f"[neginhub] token request failed | error={e}")
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')

        if not token:
            logger.error(f"[neginhub] token missing in response | meta={data.get('meta')}")
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')

        return token

    def _post(self, path: str, payload: dict, timeout: int, raise_on_unsuccess: bool = True):
        """
        Send an authenticated POST and return the parsed response dict.

        When the service answers with meta.isSuccess=False:
            - raise_on_unsuccess=True  -> InquiryServiceError (treat as failure)
            - raise_on_unsuccess=False -> None (treat as "no valid result")
        """
        token = self._get_token()

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(
                f'{self.base_url}{path}',
                headers=headers,
                json=payload,
                timeout=timeout
            )
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"[neginhub] request failed | path={path} error={e}")
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')

        meta = (data.get('meta') or {}) if isinstance(data, dict) else {}

        if not meta.get('isSuccess'):
            if raise_on_unsuccess:
                logger.error(f"[neginhub] unsuccessful response | path={path} meta={meta}")
                raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')
            logger.info(f"[neginhub] lookup returned no result | path={path} meta={meta}")
            return None

        return data

    def check_shahkar(self, national_id: str, phone_number: str) -> bool:
        data = self._post(
            'api/V5/KYC/CHECKSHAHKAR',
            {
                'mobile': phone_number,
                'nationalCode': national_id,
                'requestHandlingType': 'Standard'
            },
            timeout=5
        )
        return bool((data.get('data') or {}).get('isMatch'))

    def check_identity(self, national_id: str, birthday: str):
        return self._post(
            'api/V5/KYC/GETCIVILREGISTRYDATA',
            {
                "nationalCode": national_id,
                "birthDate": birthday.replace('/', ''),
                "trackId": str(uuid.uuid4()),
                "requestHandlingType": 0
            },
            timeout=5,
            raise_on_unsuccess=False
        )

    def check_card_ownership(self, card_number: str, national_id: str, birthday: str) -> bool:
        data = self._post(
            'api/V5/KYC/NATIONALCODEANDCARDVERIFICATION',
            {
                "NationalCode": national_id,
                "CardNumber": card_number,
                "BirthDate": birthday.replace('/', ''),
                "TrackId": str(uuid.uuid4()),
                "RequestHandlingType": 1
            },
            timeout=4
        )
        return bool((data.get('data') or {}).get('isMatch'))

    def get_card_information(self, card_number: str):
        return self._post(
            'api/V5/KYC/CARDTOIBAN',
            {
                "Card": card_number,
                "TrackId": str(uuid.uuid4()),
                "RequestHandlingType": 1
            },
            timeout=4,
            raise_on_unsuccess=False
        )
