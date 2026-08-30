from unittest.mock import MagicMock
import pytest
import requests
from django.conf import settings

from apps.core.exceptions.base import PaymentGatewayError
from apps.core.services.payment.zarrinpal import ZarinpalGateway


class TestZarinpalGateway:

    @pytest.fixture
    def gateway(self):
        return ZarinpalGateway()

    # ── Server name determination ─────────────────────────────────────────────

    def test_server_name_debug_mode(self, gateway, settings):
        settings.DEBUG = True
        assert gateway._server_name() == 'sandbox'

    def test_server_name_production_mode(self, gateway, settings):
        settings.DEBUG = False
        assert gateway._server_name() == 'payment'

    # ── process_payment ───────────────────────────────────────────────────────

    def test_process_payment_success(self, gateway, mocker, settings):
        settings.DEBUG = True
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "code": 100,
                "authority": "A00000000000000000000000000000000001",
                "message": "Success"
            },
            "errors": []
        }
        mocker.patch("requests.post", return_value=mock_resp)

        result = gateway.process_payment(amount=500_000, invoice_id=42)

        assert result["authority"] == "A00000000000000000000000000000000001"
        assert "https://sandbox.zarinpal.com/pg/StartPay/A00000000000000000000000000000000001" == result["payment_link"]

    def test_process_payment_network_exception_raises_error(self, gateway, mocker):
        mocker.patch("requests.post", side_effect=requests.RequestException("Connection failed"))

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.process_payment(amount=500_000, invoice_id=42)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)

    def test_process_payment_invalid_json_raises_error(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mocker.patch("requests.post", return_value=mock_resp)

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.process_payment(amount=500_000, invoice_id=42)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)

    def test_process_payment_with_gateway_errors_raises_error(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {},
            "errors": {"code": -9, "message": "Validation error"}
        }
        mocker.patch("requests.post", return_value=mock_resp)

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.process_payment(amount=500_000, invoice_id=42)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)

    def test_process_payment_missing_authority_raises_error(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": None,
            "errors": []
        }
        mocker.patch("requests.post", return_value=mock_resp)

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.process_payment(amount=500_000, invoice_id=42)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)

    # ── verify_payment ─────────────────────────────────────────────────────────

    def test_verify_payment_success_code_100(self, gateway, mocker):
        mock_resp = MagicMock()
        expected_data = {
            "data": {
                "code": 100,
                "ref_id": 12345678,
                "card_pan": "603799******6789",
                "card_hash": "ABCDEF123456"
            },
            "errors": []
        }
        mock_resp.json.return_value = expected_data
        mocker.patch("requests.post", return_value=mock_resp)

        result = gateway.verify_payment(authority="A0001", amount=500_000)

        assert result == expected_data

    def test_verify_payment_already_verified_code_101(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "code": 101,
                "message": "Already verified"
            },
            "errors": []
        }
        mocker.patch("requests.post", return_value=mock_resp)

        result = gateway.verify_payment(authority="A0001", amount=500_000)

        assert result == 101

    def test_verify_payment_gateway_errors_returns_102(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [],
            "errors": {"code": -51, "message": "Session is not valid"}
        }
        mocker.patch("requests.post", return_value=mock_resp)

        result = gateway.verify_payment(authority="A0001", amount=500_000)

        assert result == 102

    def test_verify_payment_unexpected_code_returns_102(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "code": -9,
                "message": "Validation error"
            },
            "errors": []
        }
        mocker.patch("requests.post", return_value=mock_resp)

        result = gateway.verify_payment(authority="A0001", amount=500_000)

        assert result == 102

    def test_verify_payment_network_exception_raises_error(self, gateway, mocker):
        mocker.patch("requests.post", side_effect=requests.RequestException("Verify timeout"))

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.verify_payment(authority="A0001", amount=500_000)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)

    def test_verify_payment_invalid_json_raises_error(self, gateway, mocker):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid response")
        mocker.patch("requests.post", return_value=mock_resp)

        with pytest.raises(PaymentGatewayError) as exc_info:
            gateway.verify_payment(authority="A0001", amount=500_000)

        assert "خطا در اتصال با درگاه پرداخت" in str(exc_info.value)
