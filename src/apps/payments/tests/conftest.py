import hashlib
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.customers.models.bank_card import BankCard
from apps.payments.models.invoice import Invoice

# ── Shared constants ──────────────────────────────────────────────────────────
PHONE_NUMBER  = '09121234567'
CARD_NUMBER   = '6037997123456789'               # 16-digit card used across tests
CARD_HASH     = hashlib.sha256(CARD_NUMBER.encode()).hexdigest().upper()
CARD_PAN      = f"{CARD_NUMBER[:6]}******{CARD_NUMBER[-4:]}"  # "603799******6789"
AUTHORITY     = 'TEST-AUTHORITY-00000000000001'  # fake Zarinpal authority string


# ── Fixtures: Users & Customers ───────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A registered user with a linked customer profile."""
    return CustomUser.objects.create(
        username=f'user-{PHONE_NUMBER}',
        phone_number=PHONE_NUMBER,
        last_ip_address='127.0.0.1',
    )


@pytest.fixture
def customer(user, db):
    """
    Returns the Customer profile that was automatically created by the
    post_save signal on CustomUser (customer_signals.py).
    """
    return user.customer_profile


@pytest.fixture
def bank_card(customer, db):
    """A verified, visible bank card belonging to the test customer."""
    return BankCard.objects.create(
        customer=customer,
        bank_name='Mellat',
        card_number=CARD_NUMBER,
        is_verified=True,
        is_show=True,
        check_again_on=timezone.now(),
    )


# ── Fixtures: Invoices ────────────────────────────────────────────────────────

@pytest.fixture
def invoice(customer, db):
    """Pending deposit invoice with a known gateway authority."""
    return Invoice.objects.create(
        customer=customer,
        total_price=500_000,
        status=Invoice.STATUS_CHOICES[0][0],   # pending
        is_paid=False,
        invoice_type=Invoice.INVOICE_TYPES[0][0],  # deposit
        gateway_track_id=AUTHORITY,
    )


@pytest.fixture
def buy_invoice(customer, db):
    """Pending buy invoice with a known gateway authority."""
    return Invoice.objects.create(
        customer=customer,
        total_price=5_000_000,
        unit_price=1_000_000,
        fee=50_000,
        maintenance_fee=10_000,
        status=Invoice.STATUS_CHOICES[0][0],   # pending
        is_paid=False,
        invoice_type=Invoice.INVOICE_TYPES[1][0],  # buy
        gateway_track_id='BUY-AUTHORITY-00000000000001',
    )


# ── Fixtures: HTTP Client ─────────────────────────────────────────────────────

@pytest.fixture
def auth_client(user):
    """APIClient authenticated with a JWT token for the test user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def api_client():
    return APIClient()


# ── Fixtures: Gateway mocks ───────────────────────────────────────────────────

@pytest.fixture
def mock_gateway_process(mocker):
    """Successful process_payment: returns a fake authority and payment link."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.process_payment',
        return_value={
            'authority': AUTHORITY,
            'payment_link': f'https://sandbox.zarinpal.com/pg/StartPay/{AUTHORITY}',
        },
    )


@pytest.fixture
def mock_gateway_verify_valid_hash(mocker):
    """verify_payment returns a card hash that matches CARD_NUMBER (sha256)."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.verify_payment',
        return_value={
            'data': {
                'card_hash': CARD_HASH,
                'card_pan': '000000******0000',  # PAN deliberately won't match alone
                'ref_id': '99999',
            }
        },
    )


@pytest.fixture
def mock_gateway_verify_valid_pan(mocker):
    """verify_payment returns a masked PAN that matches CARD_NUMBER."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.verify_payment',
        return_value={
            'data': {
                'card_hash': 'NONMATCHINGHASH',
                'card_pan': CARD_PAN,
                'ref_id': '99998',
            }
        },
    )


@pytest.fixture
def mock_gateway_verify_invalid_card(mocker):
    """verify_payment returns data that does not match any of the customer's cards."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.verify_payment',
        return_value={
            'data': {
                'card_hash': 'NONMATCHINGHASH',
                'card_pan': '000000******0000',
                'ref_id': '99997',
            }
        },
    )


@pytest.fixture
def mock_gateway_verify_101(mocker):
    """verify_payment returns 101 — payment already verified (idempotent)."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.verify_payment',
        return_value=101,
    )


@pytest.fixture
def mock_gateway_verify_102(mocker):
    """verify_payment returns 102 — payment failed at the gateway."""
    return mocker.patch(
        'apps.payments.services.payments_services.PaymentService.gateway.verify_payment',
        return_value=102,
    )


# ── Fixtures: Task mocks ──────────────────────────────────────────────────────

@pytest.fixture
def mock_task_deposit(mocker):
    """Prevents process_deposit_invoice_task from actually running."""
    return mocker.patch(
        'apps.payments.services.payments_services.process_deposit_invoice_task.apply_async',
        return_value=None,
    )


@pytest.fixture
def mock_task_buy(mocker):
    """Prevents process_buy_invoice_task from actually running."""
    return mocker.patch(
        'apps.payments.services.payments_services.process_buy_invoice_task.apply_async',
        return_value=None,
    )


# ── Fixtures: Rate limiter ────────────────────────────────────────────────────

@pytest.fixture
def mock_rate_limit(mocker):
    """Bypasses the rate limiter for all API tests."""
    return mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(True, {'limit': 100, 'remaining': 99, 'retry_after': 0}),
    )


# ── Fixtures: Notification mock (autouse) ────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_notification_service(mocker):
    """
    Prevents NotificationTemplate.DoesNotExist from being raised when
    payment-related signals fire during tests.
    """
    mocker.patch(
        'apps.notifications.services.notification_services.NotificationService.create_notification_from_template',
        return_value=None,
    )
