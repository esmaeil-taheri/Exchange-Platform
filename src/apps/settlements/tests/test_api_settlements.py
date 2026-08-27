"""
API Tests — settlements
─────────────────────────
Full request-to-response cycle for all settlement endpoints.
"""

import pytest

from apps.settlements.models.withdrawal import Withdrawal
from django.utils import timezone
from apps.core.utils.date_time_utils import get_date_time

from .conftest import WITHDRAWAL_AMT


# ═════════════════════════════════════════════════════════════════════════════
# Helper
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def withdrawal(customer, bank_card, db):
    """A pending Withdrawal for the test customer."""
    return Withdrawal.objects.create(
        customer=customer,
        card=bank_card,
        amount=WITHDRAWAL_AMT,
        settlement_method='پایا',
        remaining_wallet_amount=500_000,
    )


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/settlements/withdrawals/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestWithdrawalListApi:

    URL = '/api/v1/settlements/withdrawals/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_with_no_withdrawals_returns_empty_list(
        self, auth_client, customer
    ):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_authenticated_with_withdrawal_returns_list(
        self, auth_client, withdrawal
    ):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['amount'] == WITHDRAWAL_AMT


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/settlements/withdrawals/<withdrawal_id>/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestWithdrawalDetailApi:

    def _url(self, withdrawal_id):
        return f'/api/v1/settlements/withdrawals/{withdrawal_id}/'

    def test_unauthenticated_returns_401(self, api_client, withdrawal):
        response = api_client.get(self._url(withdrawal.id))
        assert response.status_code == 401

    def test_nonexistent_withdrawal_returns_404(self, auth_client):
        response = auth_client.get(self._url(99999))
        assert response.status_code == 404

    def test_success_returns_200_with_withdrawal_data(
        self, auth_client, withdrawal
    ):
        response = auth_client.get(self._url(withdrawal.id))
        assert response.status_code == 200
        assert response.data['data']['amount'] == WITHDRAWAL_AMT


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/settlements/withdrawals/create/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestCreateWithdrawalApi:

    URL = '/api/v1/settlements/withdrawals/create/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            self.URL, {'amount': WITHDRAWAL_AMT, 'card_id': 1}
        )
        assert response.status_code == 401

    def test_suspended_customer_returns_403(
        self, auth_client_suspended, bank_card, irt_wallet, mock_rate_limit,
        mock_withdrawal_task
    ):
        """
        A suspended account must not be able to move money out, even with a
        verified card and a sufficient balance. Suspension has to hold the funds,
        otherwise blocking a fraudulent account accomplishes nothing.
        """
        response = auth_client_suspended.post(
            self.URL, {'amount': WITHDRAWAL_AMT, 'card_id': bank_card.id}
        )
        assert response.status_code == 403
        assert Withdrawal.objects.count() == 0

    def test_preregister_customer_returns_403(
        self, auth_client, bank_card, irt_wallet, mock_rate_limit,
        mock_withdrawal_task
    ):
        """A customer who has not completed KYC cannot withdraw either."""
        response = auth_client.post(
            self.URL, {'amount': WITHDRAWAL_AMT, 'card_id': bank_card.id}
        )
        assert response.status_code == 403
        assert Withdrawal.objects.count() == 0

    def test_amount_below_minimum_returns_400(
        self, auth_client_authenticated, bank_card, mock_rate_limit
    ):
        """Amounts below 100,000 IRT are rejected by the serializer validator."""
        response = auth_client_authenticated.post(
            self.URL, {'amount': 50_000, 'card_id': bank_card.id}
        )
        assert response.status_code == 400

    def test_amount_above_maximum_returns_400(
        self, auth_client_authenticated, bank_card, mock_rate_limit
    ):
        """Amounts above 100,000,000 IRT are rejected by the serializer validator."""
        response = auth_client_authenticated.post(
            self.URL, {'amount': 200_000_000, 'card_id': bank_card.id}
        )
        assert response.status_code == 400

    def test_insufficient_balance_returns_403(
        self, auth_client_authenticated, bank_card, mock_rate_limit
    ):
        """No wallet → zero balance → InsufficientUserBalance → 403."""
        response = auth_client_authenticated.post(
            self.URL, {'amount': WITHDRAWAL_AMT, 'card_id': bank_card.id}
        )
        assert response.status_code == 403

    def test_success_returns_200_with_message(
        self, auth_client_authenticated, bank_card, irt_wallet, mock_rate_limit,
        mock_withdrawal_task
    ):
        """Valid amount with sufficient balance must create a withdrawal and return 200."""
        response = auth_client_authenticated.post(
            self.URL, {'amount': WITHDRAWAL_AMT, 'card_id': bank_card.id}
        )
        assert response.status_code == 200
        assert 'message' in response.data
