"""
API Tests — exchange
──────────────────────
Full request-to-response cycle for all exchange endpoints.
"""

from decimal import Decimal
import pytest

from apps.exchange.models.wallet import Wallet
from apps.exchange.models.transaction import Transaction
from apps.core.utils.date_time_utils import get_date_time

from .conftest import IRT_BALANCE, MOCK_PRICE_BUY, MOCK_PRICE_SELL


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/exchange/balance/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetBalanceApi:

    URL = '/api/v1/exchange/balance/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_returns_200_with_wallet_list(
        self, auth_client, customer, mocker
    ):
        """Balance endpoint must return 200 with wallets data."""
        # Mock PriceSelector to avoid requiring a price log in DB
        mocker.patch(
            'apps.exchange.selectors.price_selectors.PriceSelector.get_xau18_current_price',
            return_value={'price': 17_500_000},
        )
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert 'data' in response.data


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/exchange/transactions/?wallet_type=IRT|XAU18
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetTransactionListApi:

    URL = '/api/v1/exchange/transactions/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL, {'wallet_type': 'IRT'})
        assert response.status_code == 401

    def test_missing_wallet_type_returns_400(self, auth_client):
        """Missing wallet_type query param must return 400 Bad Request."""
        response = auth_client.get(self.URL)
        assert response.status_code == 400

    def test_irt_wallet_type_returns_200(self, auth_client, customer):
        response = auth_client.get(self.URL, {'wallet_type': 'IRT'})
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_xau_wallet_type_returns_200(self, auth_client, customer):
        response = auth_client.get(self.URL, {'wallet_type': 'XAU18'})
        assert response.status_code == 200
        assert response.data['results'] == []


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/exchange/invoice-list/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetInvoiceListApi:

    URL = '/api/v1/exchange/invoice-list/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_returns_200_empty_list(self, auth_client, customer):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['results'] == []


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/exchange/buy/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestBuyApi:

    URL = '/api/v1/exchange/buy/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            self.URL, {'amount': 1_000_000, 'aseet': 'XAU18', 'buy_from_wallet': True}
        )
        assert response.status_code == 401

    def test_non_authenticated_customer_returns_403(self, auth_client, customer, mock_rate_limit):
        """Customer with status='preregister' must be blocked by IsCustomerAuthenticated."""
        response = auth_client.post(
            self.URL, {'amount': 1_000_000, 'aseet': 'XAU18', 'buy_from_wallet': True}
        )
        assert response.status_code == 403

    def test_gateway_amount_below_min_returns_400(
        self, auth_client_authenticated, authenticated_customer, mock_rate_limit
    ):
        """Gateway buy amounts below 100,000 IRT must be rejected by the serializer."""
        response = auth_client_authenticated.post(
            self.URL,
            {'amount': 50_000, 'aseet': 'XAU18', 'buy_from_wallet': False}
        )
        assert response.status_code == 400

    def test_success_buy_from_wallet_returns_201(
        self, auth_client_authenticated, authenticated_customer,
        irt_wallet, currency, currency_balance,
        mock_site_settings, mock_price_buy, mock_daily_limit, mock_rate_limit
    ):
        """A valid wallet buy must create a transaction and return 201."""
        response = auth_client_authenticated.post(
            self.URL,
            {'amount': 1_000_000, 'aseet': 'XAU18', 'buy_from_wallet': True}
        )
        assert response.status_code == 201
        assert 'message' in response.data


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/exchange/sell/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestSellApi:

    URL = '/api/v1/exchange/sell/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            self.URL, {'amount': '0.0500', 'aseet': 'XAU18', 'card_withdaraw': False}
        )
        assert response.status_code == 401

    def test_non_authenticated_customer_returns_403(
        self, auth_client, customer, mock_rate_limit
    ):
        """Customer with status='preregister' must be blocked by IsCustomerAuthenticated."""
        response = auth_client.post(
            self.URL, {'amount': '0.0500', 'aseet': 'XAU18', 'card_withdaraw': False}
        )
        assert response.status_code == 403

    def test_success_sell_to_wallet_returns_201(
        self, auth_client_authenticated, authenticated_customer,
        xau_wallet, currency,
        mock_site_settings, mock_price_sell, mock_daily_limit, mock_rate_limit
    ):
        """A valid wallet sell must create a transaction and return 201."""
        response = auth_client_authenticated.post(
            self.URL,
            {'amount': '0.0500', 'aseet': 'XAU18', 'card_withdaraw': False}
        )
        assert response.status_code == 201
        assert 'message' in response.data
