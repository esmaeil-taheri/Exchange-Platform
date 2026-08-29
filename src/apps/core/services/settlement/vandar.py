import logging

import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class VandarClient:

    def __init__(self, token: str, business: str, base_url="https://api.vandar.io"):
        self.token = token
        self.business = business
        self.base_url = base_url
        self.wage = settings.VANDAR_SETTLEMENT_WAGE

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
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            if "access_token" in data:
                self.token = data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"

            return data

        except requests.exceptions.Timeout:
            logger.error("[vandar] refresh_token — request timed out")
            return {"error": True, "message": "Request timed out"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[vandar] refresh_token — connection error | error={e}")
            return {"error": True, "message": "Connection error"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"[vandar] refresh_token — HTTP error | status={e.response.status_code}")
            return {"error": True, "message": f"HTTP {e.response.status_code}"}

    def get_balance(self):
        url = f"{self.base_url}/v2/business/{self.business}/balance"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("[vandar] get_balance — request timed out")
            return {"error": True, "message": "Request timed out"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[vandar] get_balance — connection error | error={e}")
            return {"error": True, "message": "Connection error"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"[vandar] get_balance — HTTP error | status={e.response.status_code}")
            return {"error": True, "message": f"HTTP {e.response.status_code}"}

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
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"[vandar] create_settlement — request timed out | track_id={track_id}")
            return {
                "error": True,
                "is_timeout": True,
                "is_definitive_failure": False,
                "message": "Request timed out",
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[vandar] create_settlement — connection error | track_id={track_id} error={e}")
            return {
                "error": True,
                "is_network_error": True,
                "is_definitive_failure": False,
                "message": "Connection error",
            }
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 500
            # 4xx client errors mean Vandar rejected the request definitively (invalid IBAN, bad data, etc.)
            # 5xx server errors mean Vandar internal error / gateway timeout (unconfirmed state)
            is_definitive = 400 <= status_code < 500
            try:
                err_data = e.response.json()
                err_msg = err_data.get("message") or err_data.get("error") or str(err_data)
            except Exception:
                err_msg = f"HTTP {status_code}"
            logger.error(f"[vandar] create_settlement — HTTP error | track_id={track_id} status={status_code} definitive={is_definitive} error={err_msg}")
            return {
                "error": True,
                "is_definitive_failure": is_definitive,
                "message": err_msg,
            }
        except Exception as e:
            logger.error(f"[vandar] create_settlement — unexpected error | track_id={track_id} error={e}")
            return {
                "error": True,
                "is_definitive_failure": False,
                "message": str(e),
            }

    def inquiry_settlement(self, track_id):
        url = f"{self.base_url}/v4/business/{self.business}/settlement/{track_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"[vandar] inquiry_settlement — request timed out | track_id={track_id}")
            return {"error": True, "message": "Request timed out"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[vandar] inquiry_settlement — connection error | track_id={track_id} error={e}")
            return {"error": True, "message": "Connection error"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"[vandar] inquiry_settlement — HTTP error | track_id={track_id} status={e.response.status_code}")
            return {"error": True, "message": f"HTTP {e.response.status_code}"}

    def cancel_settlement(self, track_id, cancel_mode="PENDING"):
        url = f"{self.base_url}/v4/business/{self.business}/settlement/{track_id}"

        payload = {
            "cancel_mode": cancel_mode
        }

        try:
            response = requests.delete(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"[vandar] cancel_settlement — request timed out | track_id={track_id}")
            return {"error": True, "message": "Request timed out"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[vandar] cancel_settlement — connection error | track_id={track_id} error={e}")
            return {"error": True, "message": "Connection error"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"[vandar] cancel_settlement — HTTP error | track_id={track_id} status={e.response.status_code}")
            return {"error": True, "message": f"HTTP {e.response.status_code}"}
