import pytest
import pyotp
from unittest.mock import MagicMock
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.site_setting.models.setting import SiteSetting

# ── Shared constants ──────────────────────────────────────────────────────────
EXISTING_PHONE = '09121234567'   # a user already present in the DB
NEW_PHONE      = '09129876543'   # a user who has not registered yet
TOTP_SECRET    = 'JBSWY3DPEHPK3PXP'  # fixed secret used to generate TOTP codes in tests


# ── Cache helpers ─────────────────────────────────────────────────────────────

class SimpleCache:
    """
    Minimal in-memory cache for unit tests.
    Simulates the full behaviour of the Django cache API.
    """
    def __init__(self):
        self._store: dict = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, timeout=None):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


# ── Fixtures: Cache ───────────────────────────────────────────────────────────

@pytest.fixture
def simple_cache():
    """Returns a fresh SimpleCache instance for each test."""
    return SimpleCache()


@pytest.fixture
def mock_otp_cache(simple_cache, mocker):
    """
    Patches both the module-level otp_cache variable and caches['otp']
    (two_fa_change_status re-binds the cache locally, so both must be patched).
    """
    mock_caches = MagicMock()
    mock_caches.__getitem__ = MagicMock(return_value=simple_cache)
    mocker.patch('apps.accounts.services.user_services.otp_cache', simple_cache)
    mocker.patch('apps.accounts.services.user_services.caches', mock_caches)
    return simple_cache


@pytest.fixture(autouse=True)
def clear_otp_cache():
    """Clears the OTP cache after every test (integration tests)."""
    yield
    from django.core.cache import caches
    try:
        caches['otp'].clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def mock_notification_service(mocker):
    """
    Mocks NotificationService to prevent NotificationTemplate.DoesNotExist
    from being raised when login/register signals fire during tests.
    """
    mocker.patch(
        'apps.notifications.services.notification_services.NotificationService.create_notification_from_template',
        return_value=None,
    )


# ── Fixtures: Database ────────────────────────────────────────────────────────

@pytest.fixture
def site_settings(db):
    """SiteSetting with all features enabled."""
    obj, _ = SiteSetting.objects.get_or_create(pk=1)
    obj.customer_login = True
    obj.customer_register = True
    obj.send_welcome_sms = False
    obj.save()
    return obj


@pytest.fixture
def mock_settings(mocker, site_settings):
    """Mocks get_site_settings so tests are isolated from the DB."""
    return mocker.patch(
        'apps.accounts.services.user_services.get_site_settings',
        return_value=site_settings,
    )


@pytest.fixture
def user(db):
    """An existing user with EXISTING_PHONE."""
    return CustomUser.objects.create(
        username=f'user-{EXISTING_PHONE}',
        phone_number=EXISTING_PHONE,
        last_ip_address='127.0.0.1',
        totp_secret=TOTP_SECRET,
    )


# ── Fixtures: External Services ───────────────────────────────────────────────

@pytest.fixture
def mock_sms_success(mocker):
    """Simulates a successful SMS provider response."""
    return mocker.patch(
        'apps.accounts.services.user_services.UserService.otp_provider.send_otp',
        return_value={'code': 100},
    )


@pytest.fixture
def mock_sms_fail(mocker):
    """Simulates a failed SMS provider response."""
    return mocker.patch(
        'apps.accounts.services.user_services.UserService.otp_provider.send_otp',
        return_value={'code': 400},
    )


# ── Fixtures: HTTP Client ─────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient authenticated with a JWT token for the existing user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def mock_rate_limit(mocker):
    """
    Bypasses the rate limiter.
    Used in all API tests except those that specifically test rate limiting.
    """
    return mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(True, {'limit': 100, 'remaining': 99, 'retry_after': 0}),
    )


# ── Fixtures: TOTP ────────────────────────────────────────────────────────────

@pytest.fixture
def valid_totp():
    """Returns a currently valid TOTP code for TOTP_SECRET."""
    return pyotp.TOTP(TOTP_SECRET).now()
