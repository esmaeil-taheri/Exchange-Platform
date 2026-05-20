"""
Shared fixtures for apps.customers tests.
"""

import io
import pytest
from unittest.mock import MagicMock
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.customers.models.bank_card import BankCard
from apps.site_setting.models.setting import SiteSetting

# ── Constants ─────────────────────────────────────────────────────────────────

PHONE_NUMBER = '09121234567'
CARD_NUMBER  = '6037997123456789'   # valid Mellat BIN


def _make_minimal_jpeg() -> bytes:
    """Generates real 1x1 white JPEG bytes using Pillow (always available)."""
    try:
        from PIL import Image as PILImage
        buf = io.BytesIO()
        PILImage.new('RGB', (1, 1), color=(255, 255, 255)).save(buf, format='JPEG')
        return buf.getvalue()
    except ImportError:
        # Fallback: known-good minimal JPEG (1x1 white)
        return (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01'
            b'\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07'
            b'\xff\xd9'
        )


MINIMAL_JPEG = _make_minimal_jpeg()

IDENTITY_DATA = {
    'data': {
        'isAlive': True,
        'firstName': 'Ali',
        'lastName': 'Reza',
        'gender': 'male',
        'fatherName': 'Hassan',
    }
}


# ── Fixtures: Users & Customers ───────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A user whose Customer and Kyc records are auto-created by the post_save signal."""
    return CustomUser.objects.create(
        username=f'user-{PHONE_NUMBER}',
        phone_number=PHONE_NUMBER,
        last_ip_address='127.0.0.1',
    )


@pytest.fixture
def customer(user):
    """The Customer record auto-created by the post_save signal."""
    return user.customer_profile


@pytest.fixture
def kyc(customer):
    """The Kyc record auto-created alongside the Customer."""
    return customer.kyc


@pytest.fixture
def authenticated_customer(customer):
    """A customer with status='authenticated' (required by IsCustomerAuthenticated)."""
    customer.status = 'authenticated'
    customer.save(update_fields=['status'])
    return customer


@pytest.fixture
def bank_card(customer, db):
    """A visible BankCard linked to the customer."""
    return BankCard.objects.create(
        customer=customer,
        bank_name='Mellat Bank',
        card_number=CARD_NUMBER,
        check_again_on=timezone.now(),
    )


# ── Fixtures: HTTP Clients ────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient authenticated with a JWT for the test user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def auth_client_authenticated(user, authenticated_customer):
    """APIClient authenticated as a fully authenticated customer."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


# ── Fixtures: External-Service Mocks ─────────────────────────────────────────

@pytest.fixture
def mock_detect_bank(mocker):
    """Mocks detect_bank to avoid real bank lookup logic."""
    return mocker.patch(
        'apps.customers.services.back_card_services.detect_bank',
        return_value={'bank_title': 'Mellat Bank'},
    )


@pytest.fixture
def mock_inquiry_service(mocker):
    """
    Mocks both inquiry methods on KycService's shared inquiry_service instance.
    Shahkar passes by default; identity returns valid IDENTITY_DATA by default.
    """
    shahkar_mock = mocker.patch(
        'apps.customers.services.kyc_services.KycService.inquiry_service.check_shahkar',
        return_value=True,
    )
    identity_mock = mocker.patch(
        'apps.customers.services.kyc_services.KycService.inquiry_service.check_identity',
        return_value=IDENTITY_DATA,
    )
    return shahkar_mock, identity_mock


@pytest.fixture
def mock_minio(mocker):
    """Mocks MinioClient so no real S3 calls are made."""
    mock_cls = mocker.patch('apps.customers.services.kyc_services.MinioClient')
    instance = mock_cls.return_value
    instance.upload_file.return_value = None
    instance.generate_url.return_value = 'https://minio.example.com/kyc-documents/test.jpg'
    return instance


@pytest.fixture
def site_settings(db):
    """SiteSetting with all KYC features enabled."""
    obj, _ = SiteSetting.objects.get_or_create(pk=1)
    obj.check_mobile_ownership = True
    obj.save()
    return obj


@pytest.fixture
def mock_site_settings(mocker, site_settings):
    """Mocks get_site_settings so KYC service tests are isolated from the DB."""
    return mocker.patch(
        'apps.customers.services.kyc_services.get_site_settings',
        return_value=site_settings,
    )


@pytest.fixture
def mock_rate_limit(mocker):
    """Bypasses the rate limiter for API tests."""
    return mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(True, {'limit': 100, 'remaining': 99, 'retry_after': 0}),
    )


