from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.customers.models.bank_card import BankCard
from apps.core.services.inquiry.neginhub import InquiryService


OWNERSHIP_MAX_RETRY = 3
INFO_MAX_RETRY = 3
RETRY_DELAY_MINUTES = 1
BATCH_SIZE = 10


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def check_cards_ownership(self):

    service = InquiryService()

    cards = (
        BankCard.objects
        .select_related("customer__user")
        .filter(
            card_ownership=False,
            is_verified=None,
            is_show=True,
            ownership_counter__lt=OWNERSHIP_MAX_RETRY,
            check_again_on__lte=timezone.now()
        )
        .order_by("created_at")[:BATCH_SIZE]
    )

    for card in cards:

        try:

            customer = card.customer
            user = customer.user

            result = service.check_card_ownership(
                card_number=card.card_number,
                national_id=user.national_id,
                birthday=customer.birth_date
            )

            with transaction.atomic():

                card = BankCard.objects.select_for_update().get(id=card.id)

                if result:
                    card.card_ownership = True
                    card.reject_reason = ""
                else:
                    card.is_verified = False
                    card.reject_reason = "کد ملی مالک کارت با کد ملی مطابقت ندارد"

                card.ownership_counter += 1
                card.check_again_on = timezone.now() + timedelta(minutes=RETRY_DELAY_MINUTES)

                card.save(update_fields=[
                    "card_ownership",
                    "is_verified",
                    "reject_reason",
                    "ownership_counter",
                    "check_again_on"
                ])

        except Exception:

            card.ownership_counter += 1
            card.check_again_on = timezone.now() + timedelta(minutes=RETRY_DELAY_MINUTES)

            card.save(update_fields=[
                "ownership_counter",
                "check_again_on"
            ])



@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def complete_verified_cards_information(self):

    service = InquiryService()

    cards = (
        BankCard.objects
        .filter(
            card_ownership=True,
            is_verified=None,
            owner_information=False,
            is_show=True,
            information_counter__lt=INFO_MAX_RETRY,
            check_again_on__lte=timezone.now()
        )
        .order_by('created_at')[:BATCH_SIZE]
    )


    for card in cards:

        try:

            response = service.get_card_information(card_number=card.card_number)

            if not response:
                continue

            data = response["data"]

            with transaction.atomic():

                card = BankCard.objects.select_for_update().get(id=card.id)

                card.bank_name = data.get("bankName") or card.bank_name
                card.account_number = data.get("deposit") or "-"
                card.Shaba_number = data.get("iban") or "-"

                card.owner_information = True
                card.is_verified = True

                card.information_counter += 1
                card.check_again_on = timezone.now()

                card.save(update_fields=[
                    "bank_name",
                    "account_number",
                    "Shaba_number",
                    "owner_information",
                    "is_verified",
                    "information_counter",
                    "check_again_on"
                ])

        except Exception:

            card.information_counter += 1
            card.check_again_on = timezone.now() + timedelta(minutes=RETRY_DELAY_MINUTES)

            card.save(update_fields=[
                "information_counter",
                "check_again_on"
            ])
