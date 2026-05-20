"""
Unit Tests — KycService
─────────────────────────
Covers get_customer_identity_inquiry and submit_customer_kyc_document.
DB is used; all external I/O (Inquiry_Service, MinioClient) is mocked.
"""

import pytest
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.customers.services.kyc_services import KycService
from apps.customers.models.kyc import Kyc
from apps.customers.models.kyc_document import KycDocument
from apps.customers.exceptions.customer_exceptions import (
    CustomerAlreadyVerified,
    CustomerAlreadyUploadedDoc,
)
from apps.core.exceptions.base import ActionDisabled
from apps.core.exceptions.inquiry_exceptions import KycInquiryFailed

from .conftest import IDENTITY_DATA


# ═════════════════════════════════════════════════════════════════════════════
# get_customer_identity_inquiry
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetCustomerIdentityInquiry:

    VALID_PAYLOAD = dict(
        national_id='1234567890',
        first_name='Ali',
        last_name='Reza',
        birthday_date='1370-01-01',
    )

    def test_feature_disabled_raises_action_disabled(
        self, user, mock_site_settings, site_settings
    ):
        """When check_mobile_ownership is False, an ActionDisabled error must be raised."""
        site_settings.check_mobile_ownership = False
        site_settings.save()

        with pytest.raises(ActionDisabled):
            KycService.get_customer_identity_inquiry(user=user, **self.VALID_PAYLOAD)

    def test_already_verified_customer_raises_customer_already_verified(
        self, user, authenticated_customer, mock_site_settings, mock_inquiry_service
    ):
        """A customer with status='authenticated' must raise CustomerAlreadyVerified."""
        with pytest.raises(CustomerAlreadyVerified):
            KycService.get_customer_identity_inquiry(user=user, **self.VALID_PAYLOAD)

    def test_shahkar_failed_raises_kyc_inquiry_failed(
        self, user, mock_site_settings, mock_inquiry_service
    ):
        """A False result from check_shahkar must raise KycInquiryFailed."""
        shahkar_mock, _ = mock_inquiry_service
        shahkar_mock.return_value = False

        with pytest.raises(KycInquiryFailed):
            KycService.get_customer_identity_inquiry(user=user, **self.VALID_PAYLOAD)

    def test_deceased_user_raises_kyc_inquiry_failed(
        self, user, mock_site_settings, mock_inquiry_service
    ):
        """When isAlive is False in the identity response, KycInquiryFailed must be raised."""
        _, identity_mock = mock_inquiry_service
        identity_mock.return_value = {
            'data': {
                'isAlive': False,
                'firstName': 'Ali',
                'lastName': 'Reza',
                'gender': 'male',
                'fatherName': 'Hassan',
            }
        }

        with pytest.raises(KycInquiryFailed):
            KycService.get_customer_identity_inquiry(user=user, **self.VALID_PAYLOAD)

    def test_success_updates_user_customer_and_kyc(
        self, user, customer, kyc, mock_site_settings, mock_inquiry_service
    ):
        """On success the user name, customer fields, and kyc status must all be updated."""
        result = KycService.get_customer_identity_inquiry(user=user, **self.VALID_PAYLOAD)

        assert isinstance(result, dict)

        user.refresh_from_db()
        assert user.first_name == IDENTITY_DATA['data']['firstName']
        assert user.last_name == IDENTITY_DATA['data']['lastName']

        customer.refresh_from_db()
        assert customer.father_name == IDENTITY_DATA['data']['fatherName']
        assert customer.gender == IDENTITY_DATA['data']['gender'].lower()

        kyc.refresh_from_db()
        assert kyc.status == Kyc.Status.PENDING_UPLOAD


# ═════════════════════════════════════════════════════════════════════════════
# submit_customer_kyc_document
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSubmitCustomerKycDocument:

    def _make_doc(self, name='id_card.jpg', content_type='image/jpeg', size=1024):
        """Helper that returns a SimpleUploadedFile simulating an image upload."""
        doc = SimpleUploadedFile(name, b'x' * size, content_type=content_type)
        return doc

    def test_already_uploaded_raises_customer_already_uploaded_doc(
        self, user, kyc, mock_minio
    ):
        """Uploading when kyc.status is pending_review must raise CustomerAlreadyUploadedDoc."""
        kyc.status = Kyc.Status.PENDING_REVIEW
        kyc.save(update_fields=['status'])

        with pytest.raises(CustomerAlreadyUploadedDoc):
            KycService.submit_customer_kyc_document(
                user=user, doc=self._make_doc()
            )

    def test_success_creates_kyc_document_and_updates_kyc_status(
        self, user, kyc, mock_minio
    ):
        """On success a KycDocument row must be created and kyc.status set to pending_review."""
        kyc.status = Kyc.Status.PENDING_UPLOAD
        kyc.save(update_fields=['status'])

        result = KycService.submit_customer_kyc_document(
            user=user, doc=self._make_doc()
        )

        assert isinstance(result, dict)

        kyc.refresh_from_db()
        assert kyc.status == Kyc.Status.PENDING_REVIEW
        assert kyc.submitted_at is not None

        doc = KycDocument.objects.filter(kyc=kyc).first()
        assert doc is not None
        assert doc.image_url == 'https://minio.example.com/kyc-documents/test.jpg'
