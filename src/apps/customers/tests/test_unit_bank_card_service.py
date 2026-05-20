"""
Unit Tests — BankCardService
──────────────────────────────
Covers create_card and delete_bank_card.
DB is used; no external services involved beyond detect_bank (mocked).
"""

import pytest
from django.utils import timezone

from apps.customers.services.back_card_services import BankCardService
from apps.customers.models.bank_card import BankCard
from apps.customers.exceptions.bank_card_exceptions import (
    BankCardAlreadyExists,
    BankCardNotFound,
)

from .conftest import CARD_NUMBER


# ═════════════════════════════════════════════════════════════════════════════
# create_card
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreateCard:

    def test_duplicate_card_for_same_customer_raises_already_exists(
        self, customer, bank_card, mock_detect_bank
    ):
        """Adding the same card number for the same customer must raise BankCardAlreadyExists."""
        with pytest.raises(BankCardAlreadyExists):
            BankCardService.create_card(customer=customer, card_number=CARD_NUMBER)

    def test_card_registered_by_another_customer_raises_already_exists(
        self, user, customer, mock_detect_bank, db
    ):
        """Adding a card that already belongs to a different customer must raise BankCardAlreadyExists."""
        from apps.accounts.models.user import CustomUser
        from apps.customers.models.bank_card import BankCard

        # Create a second user/customer (signal auto-creates Customer + Kyc)
        other_user = CustomUser.objects.create(
            username='other-user-99',
            phone_number='09199999999',
            last_ip_address='127.0.0.2',
        )
        other_customer = other_user.customer_profile

        # Register the card under the other customer first
        BankCard.objects.create(
            customer=other_customer,
            bank_name='Mellat Bank',
            card_number=CARD_NUMBER,
            check_again_on=timezone.now(),
        )

        # Now attempt to add it for our test customer
        with pytest.raises(BankCardAlreadyExists):
            BankCardService.create_card(customer=customer, card_number=CARD_NUMBER)

    def test_success_returns_bank_card_with_correct_fields(
        self, customer, mock_detect_bank
    ):
        """A fresh card number must be saved with the correct bank_name and card_number."""
        card = BankCardService.create_card(customer=customer, card_number=CARD_NUMBER)

        assert card.pk is not None
        assert card.card_number == CARD_NUMBER
        assert card.bank_name == 'Mellat Bank'
        assert card.customer == customer
        assert card.is_show is True


# ═════════════════════════════════════════════════════════════════════════════
# delete_bank_card
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDeleteBankCard:

    def test_card_not_found_raises_bank_card_not_found(self, customer):
        """Deleting a non-existent card_id must raise BankCardNotFound."""
        with pytest.raises(BankCardNotFound):
            BankCardService.delete_bank_card(customer=customer, card_id=99999)

    def test_success_soft_deletes_card(self, customer, bank_card):
        """delete_bank_card must set is_show=False without removing the DB row."""
        result = BankCardService.delete_bank_card(
            customer=customer, card_id=bank_card.id
        )
        assert result is True

        bank_card.refresh_from_db()
        assert bank_card.is_show is False
