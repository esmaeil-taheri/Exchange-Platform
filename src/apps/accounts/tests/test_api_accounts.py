"""
API Tests — accounts
──────────────────────
Full request-to-response cycle is tested.
SMS provider and rate limiter are mocked.
"""

import pytest

from apps.accounts.models.user import CustomUser
from apps.core.exceptions.rate_limit_exceptions import RateLimitExceeded

from .conftest import EXISTING_PHONE, NEW_PHONE, TOTP_SECRET


# ═════════════════════════════════════════════════════════════════════════════
# OTP Send — POST /api/v1/authentication/login-register/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestOtpSendApi:

    URL = '/api/v1/authentication/login-register/'

    def test_valid_phone_new_user_returns_200(
        self, api_client, site_settings, mock_sms_success, mock_rate_limit
    ):
        response = api_client.post(self.URL, {'phone_number': NEW_PHONE})
        assert response.status_code == 200
        assert 'data' in response.data

    def test_valid_phone_existing_user_returns_200(
        self, api_client, site_settings, mock_sms_success, mock_rate_limit, user
    ):
        response = api_client.post(self.URL, {'phone_number': EXISTING_PHONE})
        assert response.status_code == 200

    def test_missing_phone_returns_400(self, api_client, mock_rate_limit):
        response = api_client.post(self.URL, {})
        assert response.status_code == 400

    def test_invalid_phone_length_returns_400(self, api_client, mock_rate_limit):
        """Phone numbers shorter or longer than 11 characters must be rejected."""
        response_short = api_client.post(self.URL, {'phone_number': '091234567'})    # 9 chars
        response_long  = api_client.post(self.URL, {'phone_number': '091234567890'}) # 12 chars
        assert response_short.status_code == 400
        assert response_long.status_code == 400

    def test_rate_limit_per_phone_returns_429(
        self, api_client, site_settings, mock_sms_success, mocker
    ):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 3, 'remaining': 0, 'retry_after': 60}),
        )
        response = api_client.post(self.URL, {'phone_number': NEW_PHONE})
        assert response.status_code == 429
        assert 'Retry-After' in response.headers

    def test_rate_limit_per_ip_returns_429(
        self, api_client, site_settings, mock_sms_success, mocker
    ):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 5, 'remaining': 0, 'retry_after': 120}),
        )
        response = api_client.post(self.URL, {'phone_number': NEW_PHONE})
        assert response.status_code == 429

    def test_rate_limit_response_has_retry_after_header(
        self, api_client, site_settings, mock_sms_success, mocker
    ):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 3, 'remaining': 0, 'retry_after': 75}),
        )
        response = api_client.post(self.URL, {'phone_number': NEW_PHONE})
        assert response.headers.get('Retry-After') == '75'


# ═════════════════════════════════════════════════════════════════════════════
# OTP Verify — POST /api/v1/authentication/verify/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestOtpVerifyApi:

    URL = '/api/v1/authentication/verify/'

    def test_valid_otp_returns_200_with_tokens(
        self, api_client, site_settings, mock_sms_success, mock_rate_limit, user
    ):
        from django.core.cache import caches
        caches['otp'].set(f'login:{EXISTING_PHONE}', '123456')

        response = api_client.post(self.URL, {
            'phone_number': EXISTING_PHONE,
            'code': '123456',
        })

        assert response.status_code == 200
        assert 'access' in response.data['detail']
        assert 'refresh' in response.data['detail']

    def test_wrong_otp_returns_400(
        self, api_client, site_settings, mock_rate_limit, user
    ):
        from django.core.cache import caches
        caches['otp'].set(f'login:{EXISTING_PHONE}', '111111')

        response = api_client.post(self.URL, {
            'phone_number': EXISTING_PHONE,
            'code': '999999',
        })
        assert response.status_code == 400

    def test_expired_otp_returns_400(self, api_client, mock_rate_limit, user):
        # cache is empty — OTP has expired
        response = api_client.post(self.URL, {
            'phone_number': EXISTING_PHONE,
            'code': '123456',
        })
        assert response.status_code == 400

    def test_rate_limit_returns_429(self, api_client, mocker, user):
        mocker.patch(
            'apps.core.utils.rate_limiter.limiter.check',
            return_value=(False, {'limit': 10, 'remaining': 0, 'retry_after': 30}),
        )
        response = api_client.post(self.URL, {
            'phone_number': EXISTING_PHONE,
            'code': '123456',
        })
        assert response.status_code == 429

    def test_first_time_login_flag_true_for_new_user(
        self, api_client, site_settings, mock_rate_limit
    ):
        from django.core.cache import caches
        caches['otp'].set(f'register:{NEW_PHONE}', '654321')

        response = api_client.post(self.URL, {
            'phone_number': NEW_PHONE,
            'code': '654321',
        })
        assert response.status_code == 200
        assert response.data['detail']['first_time_login'] is True


# ═════════════════════════════════════════════════════════════════════════════
# 2FA URI — GET /api/v1/authentication/2fa/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGet2FAUriApi:

    URL = '/api/v1/authentication/2fa/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_already_enabled_returns_403(self, auth_client, user):
        user.is_2fa_enabled = True
        user.save()
        response = auth_client.get(self.URL)
        assert response.status_code == 403

    def test_authenticated_not_enabled_returns_200(self, auth_client, user):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert 'uri' in response.data
        assert 'setup_key' in response.data


# ═════════════════════════════════════════════════════════════════════════════
# 2FA OTP Send — POST /api/v1/authentication/2fa/verify/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestVerify2FAAccessApi:

    URL = '/api/v1/authentication/2fa/verify/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, {})
        assert response.status_code == 401

    def test_authenticated_returns_200(self, auth_client, mock_rate_limit):
        response = auth_client.post(self.URL, {})
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# Change 2FA Status — POST /api/v1/authentication/2fa/change/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestChange2FAStatusApi:

    URL = '/api/v1/authentication/2fa/change/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, {})
        assert response.status_code == 401

    def test_wrong_otp_returns_400(self, auth_client, user, mock_rate_limit):
        from django.core.cache import caches
        caches['otp'].set(f'2fa:{EXISTING_PHONE}', '111111')

        response = auth_client.post(self.URL, {
            'code': '999999',
            'authenticator_code': '000000',
            'is_2fa': True,
        })
        assert response.status_code == 400

    def test_invalid_totp_returns_400(self, auth_client, user, mock_rate_limit):
        from django.core.cache import caches
        caches['otp'].set(f'2fa:{EXISTING_PHONE}', '123456')

        response = auth_client.post(self.URL, {
            'code': '123456',
            'authenticator_code': '000000',  # wrong TOTP code
            'is_2fa': True,
        })
        assert response.status_code == 400

    def test_valid_codes_enable_2fa_returns_200(
        self, auth_client, user, mock_rate_limit, valid_totp
    ):
        from django.core.cache import caches
        caches['otp'].set(f'2fa:{EXISTING_PHONE}', '123456')

        response = auth_client.post(self.URL, {
            'code': '123456',
            'authenticator_code': valid_totp,
            'is_2fa': True,
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_2fa_enabled is True

    def test_valid_codes_disable_2fa_returns_200(
        self, auth_client, user, mock_rate_limit, valid_totp
    ):
        """When 2FA is active, valid codes must disable it and return 200."""
        from django.core.cache import caches

        user.is_2fa_enabled = True
        user.save()
        caches['otp'].set(f'2fa:{EXISTING_PHONE}', '123456')

        response = auth_client.post(self.URL, {
            'code': '123456',
            'authenticator_code': valid_totp,
            'is_2fa': False,
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_2fa_enabled is False
