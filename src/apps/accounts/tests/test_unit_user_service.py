"""
Unit Tests — UserService
────────────────────────
All external dependencies (DB, Redis, SMS) are mocked.
Only the service business logic is exercised.
"""

import pytest
from django.test import RequestFactory

from apps.accounts.services.user_services import UserService
from apps.accounts.exceptions.user_exceptions import (
    OtpAlreadySent,
    FailedToSendOtp,
    InvalidOtp,
    TwoFactorAlreadyEnabled,
    TwoFactorAlreadyDisabled,
    InvalidTwoFactorCode,
)
from apps.core.exceptions.base import ActionDisabled

from .conftest import EXISTING_PHONE, NEW_PHONE, TOTP_SECRET


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_request(ip='127.0.0.1'):
    """Builds a minimal POST request with the given client IP."""
    request = RequestFactory().post('/')
    request.META['REMOTE_ADDR'] = ip
    return request


# ═════════════════════════════════════════════════════════════════════════════
# OTP Generation
# ═════════════════════════════════════════════════════════════════════════════

class TestOtpGeneration:

    def test_otp_is_six_digits(self, mock_settings, mock_otp_cache, mock_sms_success, mocker):
        mocker.patch(
            'apps.accounts.services.user_services.CustomUser.objects.filter',
            return_value=mocker.MagicMock(exists=lambda: False),
        )
        UserService.login_register(phone_number=NEW_PHONE)
        stored = mock_otp_cache.get(f'register:{NEW_PHONE}')
        assert stored is not None
        assert len(stored) == 6

    def test_otp_is_numeric(self, mock_settings, mock_otp_cache, mock_sms_success, mocker):
        mocker.patch(
            'apps.accounts.services.user_services.CustomUser.objects.filter',
            return_value=mocker.MagicMock(exists=lambda: False),
        )
        UserService.login_register(phone_number=NEW_PHONE)
        stored = mock_otp_cache.get(f'register:{NEW_PHONE}')
        assert stored.isdigit()


# ═════════════════════════════════════════════════════════════════════════════
# login_register
# ═════════════════════════════════════════════════════════════════════════════

class TestLoginRegister:

    def _patch_user_exists(self, mocker, exists: bool):
        mocker.patch(
            'apps.accounts.services.user_services.CustomUser.objects.filter',
            return_value=mocker.MagicMock(exists=lambda: exists),
        )

    def test_login_disabled_raises_action_disabled(self, mock_settings, mock_otp_cache, mocker):
        mock_settings.return_value.customer_login = False
        self._patch_user_exists(mocker, exists=True)
        with pytest.raises(ActionDisabled):
            UserService.login_register(phone_number=EXISTING_PHONE)

    def test_register_disabled_raises_action_disabled(self, mock_settings, mock_otp_cache, mocker):
        mock_settings.return_value.customer_register = False
        self._patch_user_exists(mocker, exists=False)
        with pytest.raises(ActionDisabled):
            UserService.login_register(phone_number=NEW_PHONE)

    def test_otp_already_sent_raises(self, mock_settings, mock_otp_cache, mocker):
        self._patch_user_exists(mocker, exists=False)
        mock_otp_cache.set(f'register:{NEW_PHONE}', '123456')
        with pytest.raises(OtpAlreadySent):
            UserService.login_register(phone_number=NEW_PHONE)

    def test_sms_failure_raises_and_deletes_otp(
        self, mock_settings, mock_otp_cache, mock_sms_fail, mocker
    ):
        self._patch_user_exists(mocker, exists=False)
        with pytest.raises(FailedToSendOtp):
            UserService.login_register(phone_number=NEW_PHONE)
        # OTP must be removed from cache after a failed send
        assert mock_otp_cache.get(f'register:{NEW_PHONE}') is None

    def test_success_new_user_returns_masked_phone(
        self, mock_settings, mock_otp_cache, mock_sms_success, mocker
    ):
        self._patch_user_exists(mocker, exists=False)
        result = UserService.login_register(phone_number=NEW_PHONE)
        assert 'data' in result
        assert '****' in result['data']['phone_number']

    def test_success_existing_user_returns_masked_phone(
        self, mock_settings, mock_otp_cache, mock_sms_success, mocker
    ):
        self._patch_user_exists(mocker, exists=True)
        result = UserService.login_register(phone_number=EXISTING_PHONE)
        assert 'data' in result
        assert '****' in result['data']['phone_number']


# ═════════════════════════════════════════════════════════════════════════════
# login_register_verify
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLoginRegisterVerify:

    def test_wrong_otp_raises_invalid_otp(self, mock_otp_cache, user):
        mock_otp_cache.set(f'login:{EXISTING_PHONE}', '111111')
        with pytest.raises(InvalidOtp):
            UserService.login_register_verify(
                phone_number=EXISTING_PHONE,
                code='999999',
                request=_make_request(),
            )

    def test_expired_otp_raises_invalid_otp(self, mock_otp_cache, user):
        # cache is empty — OTP has expired
        with pytest.raises(InvalidOtp):
            UserService.login_register_verify(
                phone_number=EXISTING_PHONE,
                code='123456',
                request=_make_request(),
            )

    def test_success_existing_user_returns_jwt(self, mock_otp_cache, user):
        mock_otp_cache.set(f'login:{EXISTING_PHONE}', '123456')
        result = UserService.login_register_verify(
            phone_number=EXISTING_PHONE,
            code='123456',
            request=_make_request(),
        )
        assert 'access' in result['detail']
        assert 'refresh' in result['detail']
        assert result['detail']['first_time_login'] is False

    def test_success_new_user_first_time_login_true(self, mock_otp_cache):
        mock_otp_cache.set(f'register:{NEW_PHONE}', '654321')
        result = UserService.login_register_verify(
            phone_number=NEW_PHONE,
            code='654321',
            request=_make_request(),
        )
        assert result['detail']['first_time_login'] is True

    def test_otp_deleted_after_successful_verify(self, mock_otp_cache, user):
        mock_otp_cache.set(f'login:{EXISTING_PHONE}', '123456')
        UserService.login_register_verify(
            phone_number=EXISTING_PHONE,
            code='123456',
            request=_make_request(),
        )
        assert mock_otp_cache.get(f'login:{EXISTING_PHONE}') is None


# ═════════════════════════════════════════════════════════════════════════════
# send_two_factor_otp
# ═════════════════════════════════════════════════════════════════════════════

class TestSendTwoFactorOtp:

    def test_otp_already_active_raises(self, mock_otp_cache):
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '111111')
        with pytest.raises(OtpAlreadySent):
            UserService.send_two_factor_otp(phone_number=EXISTING_PHONE)

    def test_success_stores_in_cache(self, mock_otp_cache, mock_sms_success):
        UserService.send_two_factor_otp(phone_number=EXISTING_PHONE)
        assert mock_otp_cache.get(f'2fa:{EXISTING_PHONE}') is not None
        mock_sms_success.assert_called_once()

    def test_provider_failure_clears_cache_and_raises(self, mock_otp_cache, mock_sms_fail):
        with pytest.raises(FailedToSendOtp):
            UserService.send_two_factor_otp(phone_number=EXISTING_PHONE)
        assert mock_otp_cache.get(f'2fa:{EXISTING_PHONE}') is None


# ═════════════════════════════════════════════════════════════════════════════
# setup_2fa
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSetup2FA:

    def test_already_enabled_raises(self, user, mocker):
        user.is_2fa_enabled = True
        user.save()
        request = _make_request()
        request.user = user
        with pytest.raises(TwoFactorAlreadyEnabled):
            UserService.setup_2fa(request=request)

    def test_success_returns_uri_and_setup_key(self, user):
        """setup_2fa should return a provisioning URI and the raw setup key."""
        request = _make_request()
        request.user = user

        result = UserService.setup_2fa(request=request)

        assert 'uri' in result
        assert 'setup_key' in result
        assert result['setup_key'] == TOTP_SECRET
        assert 'otpauth://totp/' in result['uri']


# ═════════════════════════════════════════════════════════════════════════════
# two_fa_change_status
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFaChangeStatus:

    def test_expired_otp_raises_invalid_otp(self, mock_otp_cache, user):
        # cache is empty — OTP has expired
        with pytest.raises(InvalidOtp):
            UserService.two_fa_change_status(
                user=user, code='123456', is_2fa=True, authenticator_code='000000'
            )

    def test_wrong_otp_raises_invalid_otp(self, mock_otp_cache, user):
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '111111')
        with pytest.raises(InvalidOtp):
            UserService.two_fa_change_status(
                user=user, code='999999', is_2fa=True, authenticator_code='000000'
            )

    def test_wrong_totp_raises_invalid_two_factor_code(self, mock_otp_cache, user):
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '123456')
        with pytest.raises(InvalidTwoFactorCode):
            UserService.two_fa_change_status(
                user=user, code='123456', is_2fa=True, authenticator_code='000000'
            )

    def test_enable_when_already_enabled_raises(self, mock_otp_cache, user, valid_totp):
        user.is_2fa_enabled = True
        user.save()
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '123456')
        with pytest.raises(TwoFactorAlreadyEnabled):
            UserService.two_fa_change_status(
                user=user, code='123456', is_2fa=True, authenticator_code=valid_totp
            )

    def test_disable_when_already_disabled_raises(self, mock_otp_cache, user, valid_totp):
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '123456')
        with pytest.raises(TwoFactorAlreadyDisabled):
            UserService.two_fa_change_status(
                user=user, code='123456', is_2fa=False, authenticator_code=valid_totp
            )

    def test_enable_success(self, mock_otp_cache, user, valid_totp):
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '123456')
        UserService.two_fa_change_status(
            user=user, code='123456', is_2fa=True, authenticator_code=valid_totp
        )
        user.refresh_from_db()
        assert user.is_2fa_enabled is True

    def test_disable_success(self, mock_otp_cache, user, valid_totp):
        user.is_2fa_enabled = True
        user.save()
        mock_otp_cache.set(f'2fa:{EXISTING_PHONE}', '123456')
        UserService.two_fa_change_status(
            user=user, code='123456', is_2fa=False, authenticator_code=valid_totp
        )
        user.refresh_from_db()
        assert user.is_2fa_enabled is False
