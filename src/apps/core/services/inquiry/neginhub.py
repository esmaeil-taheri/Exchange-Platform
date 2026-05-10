import uuid
from django.conf import settings
import requests

from apps.core.exceptions.inquiry_exceptions import InquiryServiceError


class Inquiry_Service:

    def __init__(self):
        self.BaseUrl = 'https://api.neginhub.com/'
        self.username = settings.INQUIRY_SERVICE_USERNAME
        self.password = settings.INQUIRY_SERVICE_PASSWORD
    
    def _get_token(self):
    
        headers = {
            
            "Content-Type": "application/json"
        }
        
        payload = {

            'grant_type': 'password',
            'Username': self.username,
            'Password': self.password,
        }

        try:

            response = requests.post(
                f'{self.BaseUrl}api/v5/Authentication/GetToken', 
                headers=headers, json=payload, 
                timeout=20
            )

            res = response.json()
            
            if 'access_token' in res['data']:

                return res['data']['access_token']
            
            else: 
                return False

        except: 
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')
        

    def check_shahkar(self, national_id: str, phone_number: str):

        token = self._get_token()
        
        if not token:
            return False
        
        url = f'{self.BaseUrl}api/V5/KYC/CHECKSHAHKAR'

        headers = {

            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {

            'mobile': phone_number,
            'nationalCode': national_id,
            'requestHandlingType': 'Standard'
        }

        try:

            response = requests.post(
                url, headers=headers, json=payload, 
                timeout=20
            )
            response = response.json()

            if response['meta']['isSuccess']:
                if response['data']['isMatch']:
                    return True
            else:
                return False
        except:
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')
    
    
    def check_identity(self, national_id: str, birthday: str):

        token = self._get_token()
        
        if not token:
            return False
        
        url = f'{self.BaseUrl}api/V5/KYC/GETCIVILREGISTRYDATA'

        headers = {

            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        payload = {
            "nationalCode": national_id,
            "birthDate": birthday.replace('/', ''),
            "trackId": str(uuid.uuid4()),
            "requestHandlingType": 0
        }

        try:

            response = requests.post(
                url, headers=headers, json=payload, 
                timeout=20
            )
            response = response.json()

            if response['meta']['isSuccess']:
                
                return response

            else:
                return False
        except:
            raise InquiryServiceError('خطا در اتصال به سرویس احراز هویت')