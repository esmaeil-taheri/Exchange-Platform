import requests


class VandarClient:

    wage = 6000

    def __init__(self, token: str, business: str, base_url="https://api.vandar.io"):
        self.token = token
        self.business = business
        self.base_url = base_url

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def refresh_token(self, refresh_token):

        url = f"{self.base_url}/v3/refreshtoken"

        payload = {
            "refreshtoken": refresh_token
        }

        try:

            if self.mock:
                return {
                    "token_type": "Bearer",
                    "expires_in": 432000,
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token"
                }

            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            # اگر خواستی اتوماتیک token کلاس هم آپدیت شود
            if "access_token" in data:
                self.token = data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"

            return data

        except requests.exceptions.RequestException as e:
            return {"error": True, "message": str(e)}


    def get_balance(self):
        url = f"{self.base_url}/v2/business/{self.business}/balance"

        try:
            # response = requests.get(url, headers=self.headers, timeout=10)
            # response.raise_for_status()
            # return response.json()

            mock_response = {
                "status": 1,
                "data": {
                    "wallet": 100000,
                    "wallet_deductible_amount": 70000,
                    "direct_debit_non_deductible_amount": 10000,
                    "fee_non_deductible_amount": 10000,
                    "payment_facilitator_non_deductible_amount": 10000,
                    "currency": "Toman"
                }
            }

            return mock_response

        except Exception as e:
            return {"error": True, "message": str(e)}

    def create_settlement(
        self,
        amount,
        iban,
        track_id,
        payment_number,
        description,
        national_code,
        birth_date,
        notify_url=None,
        reason_code="01",
        settlement_type="A2A",
        is_instant=1,
    ):

        url = f"{self.base_url}/v3/business/{self.business}/settlement/store"

        payload = {
            "amount": str(amount),
            "iban": iban,
            "track_id": track_id,
            "type": settlement_type,
            "is_instant": is_instant,
            "payment_number": payment_number,
            "description": description,
            "reason_code": reason_code,
            "receiver_information": {
                "national_code": national_code,
                "birth_date": birth_date
            }
        }

        if notify_url:
            payload["notify_url"] = notify_url

        try:
            # response = requests.post(
            #     url,
            #     json=payload,
            #     headers=self.headers,
            #     timeout=10
            # )
            # response.raise_for_status()
            # return response.json()

            import random
            mock_response = {
                "status": 1,
                "code": "successful",
                "data": {
                    "settlement": [
                        {
                            "id": "75ff6c40-9eaf-11f0-a22a-2703c1a6c6f1",
                            "iban": "IR430550011480005587452001",
                            "transaction_id": random.randint(10**11, 10**12 - 1),
                            "amount": 500000,
                            "amount_toman": 50000,
                            "wage_toman": 6600,
                            "payment_number": "123456",
                            "status": "PENDING",
                            "description": "Sample Settlement",
                            "settlement_date": "2025-10-01",
                            "settlement_time": "13:44:48",
                            "receipt_url": "https://vand.ar/mRX0Im",
                            "type": "ACH",
                            "is_instant": True,
                            "source": "WALLET"
                        }
                    ]
                },
                "receipt_url": "https://vand.ar/FokFOu"
            }

            return mock_response

        except Exception as e:
            return {"error": True, "message": str(e)}

    def inquiry_settlement(self, track_id):
        url = f"{self.base_url}/v4/business/{self.business}/settlement/{track_id}"

        try:
            # response = requests.get(url, headers=self.headers, timeout=10)
            # response.raise_for_status()
            # return response.json()

            mock_response = {
                "message": "جزییات تسویه با موفقیت دریافت شد.",
                "data": {
                    "track_id": track_id,
                    "receipt_url": "https://vand.ar/aaaaa",
                    "settlements": [
                        {
                            "iban": "IR410196232491332630307703",
                            "iban_owner_name": "نام صاحب حساب",
                            "transaction_id": 114355555601,
                            "amount": 21567413,
                            "wage": 902986,
                            "payment_number": "647702832910495",
                            "status": "DONE",
                            "wallet": 41231413,
                            "tracking_code": "140409120172891238",
                            "description": "توضیحات",
                            "reason_code": 10,
                            "created_at": "2025-06-11 17:44:00",
                            "receipt_url": "https://vand.ar/1abc",
                            "type": "refund",
                            "is_instant": True,
                            "source": "WALLET"
                        }
                    ]
                }
            }

            return mock_response

        except Exception as e:
            return {"error": True, "message": str(e)}

    def cancel_settlement(self, track_id, cancel_mode="PENDING"):
        url = f"{self.base_url}/v4/business/{self.business}/settlement/{track_id}"

        payload = {
            "cancel_mode": cancel_mode
        }

        try:
            # response = requests.delete(
            #     url,
            #     json=payload,
            #     headers=self.headers,
            #     timeout=10
            # )
            # response.raise_for_status()
            # return response.json()

            mock_response = {
                "message": "تسویه های زیر از این درخواست کنسل شد.",
                "data": {
                    "track_id": track_id,
                    "receipt_url": "https://vand.ar/aaaaa",
                    "settlements": [
                        {
                            "iban": "IR410196232491332630307703",
                            "iban_owner_name": "نام صاحب حساب",
                            "transaction_id": 114355555601,
                            "amount": 21567413,
                            "wage": 902986,
                            "payment_number": "647702832910495",
                            "status": "CANCELED",
                            "wallet": 41231413,
                            "tracking_code": "140409120172891238",
                            "description": "توضیحات",
                            "reason_code": 10,
                            "created_at": "2025-06-11 17:44:00",
                            "receipt_url": "https://vand.ar/1abc",
                            "type": "refund",
                            "is_instant": True,
                            "source": "WALLET"
                        }
                    ]
                }
            }

            return mock_response

        except Exception as e:
            return {"error": True, "message": str(e)}
