from datetime import timedelta
import pytest
from django.utils import timezone

from apps.customers.models.bank_card import BankCard
from apps.customers.tasks.bank_card_tasks import (
    check_cards_ownership,
    complete_verified_cards_information,
    OWNERSHIP_MAX_RETRY,
    INFO_MAX_RETRY,
)


@pytest.mark.django_db
class TestCheckCardsOwnership:

    def test_check_cards_ownership_matched(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=False,
            is_verified=None,
            is_show=True,
            ownership_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mock_check = mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.check_card_ownership",
            return_value=True,
        )

        check_cards_ownership()

        mock_check.assert_called_once_with(
            card_number=card.card_number,
            national_id=customer.user.national_id,
            birthday=customer.birth_date,
        )

        card.refresh_from_db()
        assert card.card_ownership is True
        assert card.reject_reason == ""
        assert card.ownership_counter == 1
        assert card.is_verified is None

    def test_check_cards_ownership_mismatched(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=False,
            is_verified=None,
            is_show=True,
            ownership_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.check_card_ownership",
            return_value=False,
        )

        check_cards_ownership()

        card.refresh_from_db()
        assert card.card_ownership is False
        assert card.is_verified is False
        assert card.reject_reason == "کد ملی مالک کارت با کد ملی مطابقت ندارد"
        assert card.ownership_counter == 1

    def test_check_cards_ownership_exception_increments_counter(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=False,
            is_verified=None,
            is_show=True,
            ownership_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.check_card_ownership",
            side_effect=Exception("Shahkar service timeout"),
        )

        check_cards_ownership()

        card.refresh_from_db()
        assert card.ownership_counter == 1
        assert card.card_ownership is False
        assert card.check_again_on > timezone.now()

    def test_check_cards_ownership_skips_exceeded_retries(self, customer, mocker):
        BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=False,
            is_verified=None,
            is_show=True,
            ownership_counter=OWNERSHIP_MAX_RETRY,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mock_check = mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.check_card_ownership"
        )

        check_cards_ownership()

        mock_check.assert_not_called()


@pytest.mark.django_db
class TestCompleteVerifiedCardsInformation:

    def test_complete_verified_cards_information_success(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=True,
            owner_information=False,
            is_verified=None,
            is_show=True,
            information_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mock_info = mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.get_card_information",
            return_value={
                "data": {
                    "bankName": "بانک ملت",
                    "deposit": "1234567890",
                    "iban": "IR123456789012345678901234",
                }
            },
        )

        complete_verified_cards_information()

        mock_info.assert_called_once_with(card_number=card.card_number)

        card.refresh_from_db()
        assert card.bank_name == "بانک ملت"
        assert card.account_number == "1234567890"
        assert card.Shaba_number == "IR123456789012345678901234"
        assert card.owner_information is True
        assert card.is_verified is True
        assert card.information_counter == 1

    def test_complete_verified_cards_information_no_response_skipped(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=True,
            owner_information=False,
            is_verified=None,
            is_show=True,
            information_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.get_card_information",
            return_value=None,
        )

        complete_verified_cards_information()

        card.refresh_from_db()
        assert card.owner_information is False
        assert card.is_verified is None
        assert card.information_counter == 0

    def test_complete_verified_cards_information_exception_increments_counter(self, customer, mocker):
        card = BankCard.objects.create(
            customer=customer,
            card_number="6037997123456789",
            card_ownership=True,
            owner_information=False,
            is_verified=None,
            is_show=True,
            information_counter=0,
            check_again_on=timezone.now() - timedelta(minutes=1),
        )

        mocker.patch(
            "apps.customers.tasks.bank_card_tasks.InquiryService.get_card_information",
            side_effect=Exception("Bank inquiry gateway down"),
        )

        complete_verified_cards_information()

        card.refresh_from_db()
        assert card.information_counter == 1
        assert card.owner_information is False
        assert card.is_verified is None
        assert card.check_again_on > timezone.now()
