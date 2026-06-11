"""
Integration Tests — accounts
─────────────────────────────
Real DB and real cache are used.
Only the SMS provider is mocked (external service).
"""

import pytest
from django.core.cache import caches

from apps.accounts.models.user import CustomUser
from apps.accounts.services.user_services import UserService

from .conftest import EXISTING_PHONE, NEW_PHONE


def _make_request(ip='127.0.0.1'):
    from django.test import RequestFactory
    request = RequestFactory().post('/')
    request.META['REMOTE_ADDR'] = ip
    return request


@pytest.mark.django_db
class TestOtpCacheBehavior:

    def test_otp_stored_in_cache_after_send(self, site_settings, mock_sms_success):
        UserService.login_register(phone_number=NEW_PHONE)
        otp = caches['otp'].get(f'register:{NEW_PHONE}')
        assert otp is not None
        assert len(otp) == 6

    def test_otp_deleted_from_cache_after_verify(self, site_settings, mock_sms_success):
        UserService.login_register(phone_number=NEW_PHONE)
        otp = caches['otp'].get(f'register:{NEW_PHONE}')

        UserService.login_register_verify(
            phone_number=NEW_PHONE,
            code=otp,
            request=_make_request(),
        )

        assert caches['otp'].get(f'register:{NEW_PHONE}') is None


@pytest.mark.django_db
class TestUserCreation:

    def test_new_user_created_in_db_on_first_verify(self, site_settings, mock_sms_success):
        assert not CustomUser.objects.filter(phone_number=NEW_PHONE).exists()

        UserService.login_register(phone_number=NEW_PHONE)
        otp = caches['otp'].get(f'register:{NEW_PHONE}')
        UserService.login_register_verify(
            phone_number=NEW_PHONE,
            code=otp,
            request=_make_request(),
        )

        assert CustomUser.objects.filter(phone_number=NEW_PHONE).exists()

    def test_last_login_and_ip_updated_on_existing_user_login(
        self, site_settings, mock_sms_success, user
    ):
        original_ip = user.last_ip_address

        UserService.login_register(phone_number=EXISTING_PHONE)
        otp = caches['otp'].get(f'login:{EXISTING_PHONE}')
        UserService.login_register_verify(
            phone_number=EXISTING_PHONE,
            code=otp,
            request=_make_request(ip='10.0.0.1'),
        )

        user.refresh_from_db()
        assert user.last_ip_address == '10.0.0.1'
        assert user.last_ip_address != original_ip


@pytest.mark.django_db
class TestTwoFaStatusPersistence:

    def test_2fa_status_persisted_to_db(self, user, valid_totp):
        caches['otp'].set(f'2fa:{EXISTING_PHONE}', '123456')

        UserService.two_fa_change_status(
            user=user,
            code='123456',
            is_2fa=True,
            authenticator_code=valid_totp,
        )

        user.refresh_from_db()
        assert user.is_2fa_enabled is True


@pytest.mark.django_db
class TestSendTwoFactorOtpIntegration:

    def test_2fa_otp_stored_in_real_cache(self, mock_sms_success):
        """send_two_factor_otp must write a 6-digit OTP to the real cache."""
        UserService.send_two_factor_otp(phone_number=EXISTING_PHONE)
        otp = caches['otp'].get(f'2fa:{EXISTING_PHONE}')
        assert otp is not None
        assert len(otp) == 6
        assert otp.isdigit()


@pytest.mark.django_db
class TestLoginSignal:

    def test_login_detected_signal_fires_on_existing_user_login(
        self, site_settings, mock_sms_success, user
    ):
        """login_detected signal must be sent when an existing user logs in."""
        from apps.accounts.services.user_services import login_detected

        fired_users = []

        def capture_handler(sender, user, **kwargs):
            fired_users.append(user)

        login_detected.connect(capture_handler)
        try:
            UserService.login_register(phone_number=EXISTING_PHONE)
            otp = caches['otp'].get(f'login:{EXISTING_PHONE}')
            UserService.login_register_verify(
                phone_number=EXISTING_PHONE,
                code=otp,
                request=_make_request(),
            )
        finally:
            login_detected.disconnect(capture_handler)

        assert len(fired_users) == 1
        assert fired_users[0].phone_number == EXISTING_PHONE
