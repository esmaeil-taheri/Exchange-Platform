"""
Integration Tests — customers
───────────────────────────────
Real DB transactions.  Verifies that service calls produce the correct
persistent state end-to-end.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.customers.services.back_card_services import BankCardService
from apps.customers.services.kyc_services import KycService
from apps.customers.models.bank_card import BankCard
from apps.customers.models.kyc import Kyc
from apps.customers.models.kyc_document import KycDocument

from .conftest import CARD_NUMBER, IDENTITY_DATA


# ═════════════════════════════════════════════════════════════════════════════
# BankCard persistence
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBankCardIntegration:

    def test_card_created_and_persisted_in_db(self, customer, mock_detect_bank):
        """create_card must produce a persisted BankCard row with is_show=True."""
        assert BankCard.objects.filter(customer=customer).count() == 0

        BankCardService.create_card(customer=customer, card_number=CARD_NUMBER)

        assert BankCard.objects.filter(customer=customer).count() == 1
        card = BankCard.objects.get(customer=customer)
        assert card.card_number == CARD_NUMBER
        assert card.is_show is True

    def test_soft_delete_persists_is_show_false(self, customer, bank_card):
        """delete_bank_card must flip is_show to False without deleting the DB row."""
        BankCardService.delete_bank_card(customer=customer, card_id=bank_card.id)

        assert BankCard.objects.filter(customer=customer).count() == 1
        card = BankCard.objects.get(customer=customer)
        assert card.is_show is False


# ═════════════════════════════════════════════════════════════════════════════
# KYC full identity inquiry
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestKycServiceIntegration:

    def test_full_identity_inquiry_persists_state(
        self, user, customer, kyc, mock_site_settings, mock_inquiry_service
    ):
        """
        A complete identity inquiry must persist:
          - kyc.status = pending_upload
          - user first/last name from inquiry response
          - customer gender and father_name from inquiry response
        """
        KycService.get_customer_identity_inquiry(
            user=user,
            national_id='1234567890',
            first_name='Ali',
            last_name='Reza',
            birthday_date='1370-01-01',
        )

        kyc.refresh_from_db()
        assert kyc.status == Kyc.Status.PENDING_UPLOAD
        assert kyc.shahkar_check is True

        user.refresh_from_db()
        assert user.first_name == IDENTITY_DATA['data']['firstName']
        assert user.last_name == IDENTITY_DATA['data']['lastName']

        customer.refresh_from_db()
        assert customer.father_name == IDENTITY_DATA['data']['fatherName']
