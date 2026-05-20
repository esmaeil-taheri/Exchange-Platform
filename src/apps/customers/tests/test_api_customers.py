"""
API Tests — customers
──────────────────────
Full request-to-response cycle for all customer endpoints.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.customers.models.kyc import Kyc

from .conftest import CARD_NUMBER, MINIMAL_JPEG


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/customers/profile/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetCustomerProfileApi:

    URL = '/api/v1/customers/profile/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_returns_200_with_profile(self, auth_client, user, customer):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert 'detail' in response.data
        assert response.data['detail']['phone_number'] == user.phone_number


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/customers/kyc/status/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetCustomerKycStatusApi:

    URL = '/api/v1/customers/kyc/status/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_returns_200_with_kyc_level(self, auth_client, kyc):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['detail']['kyc_level'] == Kyc.Status.NOT_STARTED


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/customers/card/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBankCardListApi:

    URL = '/api/v1/customers/card/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_non_authenticated_customer_returns_403(self, auth_client, customer):
        """Customer with status='preregister' must be blocked by IsCustomerAuthenticated."""
        response = auth_client.get(self.URL)
        assert response.status_code == 403

    def test_authenticated_customer_with_no_cards_returns_empty_list(
        self, auth_client_authenticated, authenticated_customer
    ):
        response = auth_client_authenticated.get(self.URL)
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_authenticated_customer_returns_their_cards(
        self, auth_client_authenticated, authenticated_customer, bank_card
    ):
        response = auth_client_authenticated.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['card_number'] == CARD_NUMBER


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/customers/card/create
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreateBankCardApi:

    URL = '/api/v1/customers/card/create'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, {'card_number': CARD_NUMBER})
        assert response.status_code == 401

    def test_non_authenticated_customer_returns_403(self, auth_client):
        response = auth_client.post(self.URL, {'card_number': CARD_NUMBER})
        assert response.status_code == 403

    def test_invalid_card_number_returns_400(
        self, auth_client_authenticated, authenticated_customer
    ):
        response = auth_client_authenticated.post(
            self.URL, {'card_number': '1234567890123456'}
        )
        assert response.status_code == 400

    def test_success_returns_200_with_card_data(
        self, auth_client_authenticated, authenticated_customer, mock_detect_bank
    ):
        response = auth_client_authenticated.post(
            self.URL, {'card_number': CARD_NUMBER}
        )
        assert response.status_code == 200
        assert response.data['card_number'] == CARD_NUMBER
        assert response.data['bank_name'] == 'Mellat Bank'

    def test_duplicate_card_returns_400(
        self, auth_client_authenticated, authenticated_customer,
        bank_card, mock_detect_bank
    ):
        """Submitting a card that already exists for this customer must return 400.
        BankCardAlreadyExists is mapped to HTTP 400 in the custom exception handler."""
        response = auth_client_authenticated.post(
            self.URL, {'card_number': CARD_NUMBER}
        )
        assert response.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# DELETE /api/v1/customers/card/<card_id>
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDeleteBankCardApi:

    def _url(self, card_id):
        return f'/api/v1/customers/card/{card_id}'

    def test_unauthenticated_returns_401(self, api_client, bank_card):
        response = api_client.delete(self._url(bank_card.id))
        assert response.status_code == 401

    def test_non_authenticated_customer_returns_403(self, auth_client, bank_card):
        response = auth_client.delete(self._url(bank_card.id))
        assert response.status_code == 403

    def test_card_not_found_returns_404(
        self, auth_client_authenticated, authenticated_customer
    ):
        response = auth_client_authenticated.delete(self._url(99999))
        assert response.status_code == 404

    def test_success_returns_204(
        self, auth_client_authenticated, authenticated_customer, bank_card
    ):
        response = auth_client_authenticated.delete(self._url(bank_card.id))
        assert response.status_code == 204


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/customers/kyc/verify-identity/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIdentityInquiryApi:

    URL = '/api/v1/customers/kyc/verify-identity/'

    VALID_PAYLOAD = {
        'national_id': '1234567890',
        'first_name': 'Ali',
        'last_name': 'Reza',
        'birthday': '1370-01-01',
    }

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert response.status_code == 401

    def test_missing_fields_returns_400(self, auth_client, mock_rate_limit):
        response = auth_client.post(self.URL, {})
        assert response.status_code == 400

    def test_success_returns_200(
        self, auth_client, mock_rate_limit, mock_site_settings, mock_inquiry_service
    ):
        response = auth_client.post(self.URL, self.VALID_PAYLOAD)
        assert response.status_code == 200
        assert 'message' in response.data

    def test_feature_disabled_returns_error(
        self, auth_client, mock_rate_limit, mock_site_settings, site_settings
    ):
        """When check_mobile_ownership=False the endpoint must return a non-200 error."""
        site_settings.check_mobile_ownership = False
        site_settings.save()

        response = auth_client.post(self.URL, self.VALID_PAYLOAD)
        assert response.status_code != 200


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/customers/kyc/upload-doc/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestKycUploadDocApi:

    URL = '/api/v1/customers/kyc/upload-doc/'

    def _make_image(self, name='card.jpg', content_type='image/jpeg'):
        """Returns a real minimal JPEG that passes Pillow image validation."""
        return SimpleUploadedFile(name, MINIMAL_JPEG, content_type=content_type)

    def test_unauthenticated_returns_401(self, api_client):
        doc = self._make_image()
        response = api_client.post(
            self.URL, {'national_card_image': doc}, format='multipart'
        )
        assert response.status_code == 401

    def test_wrong_kyc_status_returns_403(self, auth_client, kyc, mock_rate_limit):
        """kyc.status=not_started must be blocked by CanUploadKycDocument (returns 403)."""
        response = auth_client.post(
            self.URL,
            {'national_card_image': self._make_image()},
            format='multipart',
        )
        assert response.status_code == 403

    def test_success_returns_200(self, auth_client, kyc, mock_minio, mock_rate_limit):
        """With kyc.status=pending_upload the upload must succeed and return 200."""
        kyc.status = Kyc.Status.PENDING_UPLOAD
        kyc.save(update_fields=['status'])

        response = auth_client.post(
            self.URL,
            {'national_card_image': self._make_image()},
            format='multipart',
        )
        assert response.status_code == 200
        assert 'message' in response.data
