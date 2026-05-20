"""
Shared fixtures for apps.settlements tests.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.customers.models.bank_card import BankCard
from apps.exchange.models.wallet import Wallet
from apps.core.utils.date_time_utils import get_date_time

# ── Constants ─────────────────────────────────────────────────────────────────

PHONE_NUMBER   = '09121234567'
CARD_NUMBER    = '6037997123456789'
WITHDRAWAL_AMT = 500_000       # 500,000 IRT — valid range and within balance
WALLET_BALANCE = 1_000_000     # initial IRT balance seeded into DB


# ── Fixtures: User & Customer ─────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A user whose Customer and Kyc are auto-created by the post_save signal."""
    return CustomUser.objects.create(
        username=f'user-{PHONE_NUMBER}',
        phone_number=PHONE_NUMBER,
        last_ip_address='127.0.0.1',
    )


@pytest.fixture
def customer(user):
    """Customer auto-created by the post_save signal."""
    return user.customer_profile


@pytest.fixture
def bank_card(customer, db):
    """
    A verified BankCard.
    BankCardSelectors.get_customer_card_by_id requires is_verified=True
    and is_show=True to return the card.
    """
    return BankCard.objects.create(
        customer=customer,
        bank_name='Mellat Bank',
        card_number=CARD_NUMBER,
        is_verified=True,
        is_show=True,
        check_again_on=timezone.now(),
    )


@pytest.fixture
def irt_wallet(customer, db):
    """
    A single verified IRT wallet entry giving the customer WALLET_BALANCE.
    WalletSelector.get_user_balance_for_update aggregates amount across all
    verified IRT wallet rows, so one row is enough.
    """
    ts = get_date_time()['timestamp']
    return Wallet.objects.create(
        customer=customer,
        wallet_type='irt',
        amount=WALLET_BALANCE,
        desc='test deposit',
        ip='127.0.0.1',
        created_at=ts,
        verified_at=ts,
        is_verified=True,
    )


# ── Fixtures: HTTP Clients ────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient with a valid JWT for the test user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


# ── Fixtures: External-Service Mocks ─────────────────────────────────────────

@pytest.fixture
def mock_withdrawal_task(mocker):
    """
    Prevents the real Celery task from being dispatched.
    process_withdrawal_requests.apply_async would connect to a broker, so it
    must be mocked in every test that calls initiate_withdrawal_request.
    """
    return mocker.patch(
        'apps.settlements.services.settlement_services.process_withdrawal_requests.apply_async',
        return_value=None,
    )


@pytest.fixture
def mock_rate_limit(mocker):
    """Bypasses the rate limiter for API tests."""
    return mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(True, {'limit': 100, 'remaining': 99, 'retry_after': 0}),
    )
