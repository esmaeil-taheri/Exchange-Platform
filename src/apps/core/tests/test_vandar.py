from unittest.mock import MagicMock
import pytest
import requests

from apps.core.services.settlement.vandar import VandarClient


class TestVandarClient:

    @pytest.fixture
    def client(self):
        return VandarClient(
            token="test-token-12345",
            business="my-gold-business",
            base_url="https://api.vandar.io"
        )

    # ── Initialization ────────────────────────────────────────────────────────

    def test_init_attributes(self, client):
        assert client.token == "test-token-12345"
        assert client.business == "my-gold-business"
        assert client.base_url == "https://api.vandar.io"
        assert client.headers["Authorization"] == "Bearer test-token-12345"
        assert client.headers["Content-Type"] == "application/json"

    # ── refresh_token ─────────────────────────────────────────────────────────

    def test_refresh_token_success(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "new-access-token-99999",
            "token_type": "Bearer"
        }
        mocker.patch("requests.post", return_value=mock_resp)

        result = client.refresh_token("dummy-refresh-token")

        assert result["access_token"] == "new-access-token-99999"
        assert client.token == "new-access-token-99999"
        assert client.headers["Authorization"] == "Bearer new-access-token-99999"

    def test_refresh_token_missing_access_token_field(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": 0, "message": "Invalid token"}
        mocker.patch("requests.post", return_value=mock_resp)

        result = client.refresh_token("dummy-refresh-token")

        assert result["status"] == 0
        assert client.token == "test-token-12345"

    def test_refresh_token_timeout(self, client, mocker):
        mocker.patch("requests.post", side_effect=requests.exceptions.Timeout)

        result = client.refresh_token("dummy-refresh-token")

        assert result["error"] is True
        assert result["message"] == "Request timed out"

    def test_refresh_token_connection_error(self, client, mocker):
        mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("DNS failure"))

        result = client.refresh_token("dummy-refresh-token")

        assert result["error"] is True
        assert result["message"] == "Connection error"

    def test_refresh_token_http_error(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.post", side_effect=err)

        result = client.refresh_token("dummy-refresh-token")

        assert result["error"] is True
        assert result["message"] == "HTTP 401"

    # ── get_balance ───────────────────────────────────────────────────────────

    def test_get_balance_success(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": 1,
            "balance": 150_000_000
        }
        mocker.patch("requests.get", return_value=mock_resp)

        result = client.get_balance()

        assert result["status"] == 1
        assert result["balance"] == 150_000_000

    def test_get_balance_timeout(self, client, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.Timeout)

        result = client.get_balance()

        assert result["error"] is True
        assert result["message"] == "Request timed out"

    def test_get_balance_connection_error(self, client, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.ConnectionError)

        result = client.get_balance()

        assert result["error"] is True
        assert result["message"] == "Connection error"

    def test_get_balance_http_error(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.get", side_effect=err)

        result = client.get_balance()

        assert result["error"] is True
        assert result["message"] == "HTTP 500"

    # ── create_settlement ─────────────────────────────────────────────────────

    def test_create_settlement_success(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": 1,
            "data": {
                "settlement": [
                    {
                        "track_id": "101",
                        "status": "PENDING",
                        "amount": 1_000_000
                    }
                ]
            }
        }
        mock_post = mocker.patch("requests.post", return_value=mock_resp)

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR123456789012345678901234",
            track_id="101",
            payment_number="PAY-101",
            description="تسویه فروش طلا",
            national_code="0012345678",
            birth_date="1370/01/01",
            notify_url="https://example.com/webhook/settlement"
        )

        assert result["status"] == 1
        assert result["data"]["settlement"][0]["track_id"] == "101"
        payload = mock_post.call_args[1]["json"]
        assert payload["notify_url"] == "https://example.com/webhook/settlement"
        assert payload["receiver_information"]["national_code"] == "0012345678"

    def test_create_settlement_timeout(self, client, mocker):
        mocker.patch("requests.post", side_effect=requests.exceptions.Timeout)

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR12",
            track_id="102",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_timeout"] is True
        assert result["is_definitive_failure"] is False

    def test_create_settlement_connection_error(self, client, mocker):
        mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("Socket closed"))

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR12",
            track_id="103",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_network_error"] is True
        assert result["is_definitive_failure"] is False

    def test_create_settlement_http_400_definitive_failure(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": "Invalid IBAN number"}
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.post", side_effect=err)

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR_BAD",
            track_id="104",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_definitive_failure"] is True
        assert result["message"] == "Invalid IBAN number"

    def test_create_settlement_http_400_unparsable_json(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.side_effect = ValueError("Not JSON")
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.post", side_effect=err)

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR_BAD",
            track_id="105",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_definitive_failure"] is True
        assert result["message"] == "HTTP 400"

    def test_create_settlement_http_503_non_definitive_failure(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"message": "Service Unavailable"}
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.post", side_effect=err)

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR12",
            track_id="106",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_definitive_failure"] is False
        assert result["message"] == "Service Unavailable"

    def test_create_settlement_generic_exception(self, client, mocker):
        mocker.patch("requests.post", side_effect=RuntimeError("Unexpected crash"))

        result = client.create_settlement(
            amount=1_000_000,
            iban="IR12",
            track_id="107",
            payment_number="P",
            description="D",
            national_code="N",
            birth_date="B"
        )

        assert result["error"] is True
        assert result["is_definitive_failure"] is False
        assert "Unexpected crash" in result["message"]

    # ── inquiry_settlement ────────────────────────────────────────────────────

    def test_inquiry_settlement_success(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": 1,
            "data": {
                "status": "DONE",
                "track_id": "108"
            }
        }
        mocker.patch("requests.get", return_value=mock_resp)

        result = client.inquiry_settlement(track_id="108")

        assert result["status"] == 1
        assert result["data"]["status"] == "DONE"

    def test_inquiry_settlement_timeout(self, client, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.Timeout)

        result = client.inquiry_settlement(track_id="108")

        assert result["error"] is True
        assert result["message"] == "Request timed out"

    def test_inquiry_settlement_connection_error(self, client, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.ConnectionError)

        result = client.inquiry_settlement(track_id="108")

        assert result["error"] is True
        assert result["message"] == "Connection error"

    def test_inquiry_settlement_http_404_not_found(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.get", side_effect=err)

        result = client.inquiry_settlement(track_id="109")

        assert result["error"] is True
        assert result["is_not_found"] is True
        assert result["status_code"] == 404

    def test_inquiry_settlement_http_500_error(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.get", side_effect=err)

        result = client.inquiry_settlement(track_id="110")

        assert result["error"] is True
        assert result["is_not_found"] is False
        assert result["status_code"] == 500

    # ── cancel_settlement ─────────────────────────────────────────────────────

    def test_cancel_settlement_success(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": 1,
            "message": "Settlement cancelled"
        }
        mocker.patch("requests.delete", return_value=mock_resp)

        result = client.cancel_settlement(track_id="111", cancel_mode="PENDING")

        assert result["status"] == 1
        assert result["message"] == "Settlement cancelled"

    def test_cancel_settlement_timeout(self, client, mocker):
        mocker.patch("requests.delete", side_effect=requests.exceptions.Timeout)

        result = client.cancel_settlement(track_id="111")

        assert result["error"] is True
        assert result["message"] == "Request timed out"

    def test_cancel_settlement_connection_error(self, client, mocker):
        mocker.patch("requests.delete", side_effect=requests.exceptions.ConnectionError)

        result = client.cancel_settlement(track_id="111")

        assert result["error"] is True
        assert result["message"] == "Connection error"

    def test_cancel_settlement_http_error(self, client, mocker):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        err = requests.exceptions.HTTPError(response=mock_resp)
        mocker.patch("requests.delete", side_effect=err)

        result = client.cancel_settlement(track_id="111")

        assert result["error"] is True
        assert result["message"] == "HTTP 400"
