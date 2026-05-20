"""
API Tests — payments
──────────────────────
Full request-to-response cycle is tested.
Gateway, tasks, and rate limiter are mocked.
"""

import pytest

from apps.payments.models.invoice import Invoice

from .conftest import AUTHORITY


# ═════════════════════════════════════════════════════════════════════════════
# Zarinpal Callback — POST /api/v1/payments/zarinpal/callback
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestZarinpalCallbackApi:

    URL = '/api/v1/payments/zarinpal/callback'

    def test_missing_gateway_track_id_returns_400(self, api_client, mock_rate_limit):
        response = api_client.post(self.URL, {})
        assert response.status_code == 400

    def test_invoice_not_found_returns_error(self, api_client, mock_rate_limit):
        response = api_client.post(self.URL, {'gateway_track_id': 'UNKNOWN'})
        assert response.status_code in (400, 404)

    def test_valid_callback_returns_200(
        self, api_client, mock_rate_limit,
        invoice, bank_card,
        mock_gateway_verify_valid_hash, mock_task_deposit,
    ):
        response = api_client.post(self.URL, {'gateway_track_id': AUTHORITY})
        assert response.status_code == 200
        assert 'message' in response.data

    def test_rate_limit_returns_429(self, api_client, mocker):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 20, 'remaining': 0, 'retry_after': 60}),
        )
        response = api_client.post(self.URL, {'gateway_track_id': AUTHORITY})
        assert response.status_code == 429
        assert 'Retry-After' in response.headers


# ═════════════════════════════════════════════════════════════════════════════
# Deposit — POST /api/v1/payments/deposit
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDepositApi:

    URL = '/api/v1/payments/deposit'

    def test_unauthenticated_returns_401(self, api_client, mock_rate_limit):
        response = api_client.post(self.URL, {'amount': 500_000})
        assert response.status_code == 401

    def test_amount_below_minimum_returns_400(
        self, auth_client, customer, mock_rate_limit
    ):
        response = auth_client.post(self.URL, {'amount': 50_000})  # below 100,000
        assert response.status_code == 400

    def test_amount_above_maximum_returns_400(
        self, auth_client, customer, mock_rate_limit
    ):
        response = auth_client.post(self.URL, {'amount': 200_000_000})  # above 100,000,000
        assert response.status_code == 400

    def test_valid_amount_returns_200_with_payment_link(
        self, auth_client, customer, mock_rate_limit, mock_gateway_process
    ):
        response = auth_client.post(self.URL, {'amount': 500_000})
        assert response.status_code == 200
        assert 'message' in response.data
        assert 'zarinpal.com' in response.data['message']

    def test_rate_limit_returns_429(self, auth_client, customer, mocker):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 3, 'remaining': 0, 'retry_after': 300}),
        )
        response = auth_client.post(self.URL, {'amount': 500_000})
        assert response.status_code == 429
        assert 'Retry-After' in response.headers
