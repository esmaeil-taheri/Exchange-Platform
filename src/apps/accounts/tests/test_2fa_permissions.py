import pytest
from django.core.cache import caches
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import EXISTING_PHONE


URL = '/api/v1/authentication/2fa/login/verify/'
PROTECTED_URL = '/api/v1/authentication/2fa/verify/'


@pytest.mark.django_db
def test_login_2fa_requires_authentication(api_client):
    assert api_client.post(URL, {'authenticator_code': '123456'}).status_code == 401


@pytest.mark.django_db
def test_two_factor_gate(auth_client, user, valid_totp, mock_rate_limit, mock_sms_success):
    user.is_2fa_enabled = True
    user.requires_2fa = True
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    assert auth_client.post(PROTECTED_URL).status_code == 403
    assert auth_client.post(URL, {'authenticator_code': 'bad'}).status_code == 400
    wrong_code = str((int(valid_totp) + 1) % 1000000).zfill(6)
    assert auth_client.post(URL, {'authenticator_code': wrong_code}).status_code == 400
    user.refresh_from_db()
    assert user.requires_2fa is True

    response = auth_client.post(URL, {'authenticator_code': valid_totp})
    assert response.status_code == 200
    assert set(response.data) == {'message'}
    user.refresh_from_db()
    assert user.requires_2fa is False
    assert auth_client.post(PROTECTED_URL).status_code == 200


@pytest.mark.django_db
def test_users_without_2fa_keep_access(auth_client, mock_rate_limit, mock_sms_success):
    assert auth_client.post(PROTECTED_URL).status_code == 200


@pytest.mark.django_db
def test_force_authenticated_user_cannot_bypass_2fa(auth_client, user):
    user.is_2fa_enabled = True
    user.requires_2fa = True
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    auth_client.force_authenticate(user=user)
    assert auth_client.post(PROTECTED_URL).status_code == 403


@pytest.mark.django_db
def test_two_factor_verification_is_rate_limited(auth_client, mocker):
    mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(False, {'retry_after': 300}),
    )
    response = auth_client.post(URL, {'authenticator_code': '123456'})
    assert response.status_code == 429


@pytest.mark.django_db
def test_other_domains_require_2fa(auth_client, user):
    user.is_2fa_enabled = True
    user.requires_2fa = True
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    assert auth_client.get('/api/v1/notifications/').status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('enabled,required,expected', [
    (False, False, 200), (False, True, 200),
    (True, False, 200), (True, True, 403),
])
def test_permission_uses_both_flags(auth_client, user, mock_rate_limit, mock_sms_success, enabled, required, expected):
    user.is_2fa_enabled = enabled
    user.requires_2fa = required
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    assert auth_client.post(PROTECTED_URL).status_code == expected


@pytest.mark.django_db
@pytest.mark.parametrize('enabled', [True, False])
def test_login_resets_requirement(api_client, user, site_settings, mock_rate_limit, enabled):
    user.is_2fa_enabled = enabled
    user.requires_2fa = not enabled
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    caches['otp'].set(f'login:{EXISTING_PHONE}', '123456')
    response = api_client.post('/api/v1/authentication/verify/', {
        'phone_number': EXISTING_PHONE, 'code': '123456',
    })
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.requires_2fa is enabled
    refresh = RefreshToken(response.data['detail']['refresh'])
    assert 'two_fa_verified' not in refresh


@pytest.mark.django_db
def test_verification_does_not_issue_tokens(auth_client, user, valid_totp, mock_rate_limit, mocker):
    user.is_2fa_enabled = True
    user.requires_2fa = True
    user.save(update_fields=['is_2fa_enabled', 'requires_2fa'])
    issue_token = mocker.patch('apps.accounts.services.user_services.RefreshToken.for_user')
    response = auth_client.post(URL, {'authenticator_code': valid_totp})
    assert response.status_code == 200
    issue_token.assert_not_called()
