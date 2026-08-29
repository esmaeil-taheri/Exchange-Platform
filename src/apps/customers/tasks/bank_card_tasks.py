from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.customers.models.bank_card import BankCard
from apps.core.services.inquiry.neginhub import InquiryService
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)

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

    count = cards.count()
    if count > 0:
        logger.info(f"[task=check_cards_ownership] Batch started | count={count}")

    for card in cards:
        card_masked = f"{card.card_number[:6]}******{card.card_number[-4:]}" if len(card.card_number) >= 10 else card.card_number

        try:
            customer = card.customer
            user = customer.user

            logger.info(
                f"[task=check_cards_ownership] Inquiring ownership | card_id={card.id} "
                f"card={card_masked} customer_id={customer.id}"
            )

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
                    logger.info(
                        f"[task=check_cards_ownership] Ownership MATCHED | card_id={card.id} "
                        f"card={card_masked} customer_id={customer.id}"
                    )
                else:
                    card.is_verified = False
                    card.reject_reason = "کد ملی مالک کارت با کد ملی مطابقت ندارد"
                    logger.warning(
                        f"[task=check_cards_ownership] Ownership MISMATCH | card_id={card.id} "
                        f"card={card_masked} customer_id={customer.id} reason='{card.reject_reason}'"
                    )

                card.ownership_counter += 1
                card.check_again_on = timezone.now() + timedelta(minutes=RETRY_DELAY_MINUTES)

                card.save(update_fields=[
                    "card_ownership",
                    "is_verified",
                    "reject_reason",
                    "ownership_counter",
                    "check_again_on"
                ])

        except Exception as exc:
            logger.error(
                f"[task=check_cards_ownership] Inquiry failed | card_id={card.id} "
                f"card={card_masked} attempt={card.ownership_counter + 1} error={exc}"
            )

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

    count = cards.count()
    if count > 0:
        logger.info(f"[task=card_info] Batch started | count={count}")

    for card in cards:
        card_masked = f"{card.card_number[:6]}******{card.card_number[-4:]}" if len(card.card_number) >= 10 else card.card_number

        try:
            logger.info(f"[task=card_info] Fetching card info | card_id={card.id} card={card_masked}")
            response = service.get_card_information(card_number=card.card_number)

            if not response:
                logger.warning(f"[task=card_info] No response from inquiry service | card_id={card.id}")
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

                logger.info(
                    f"[task=card_info] Card info COMPLETED | card_id={card.id} "
                    f"bank_name={card.bank_name} iban={card.Shaba_number}"
                )

        except Exception as exc:
            logger.error(
                f"[task=card_info] Fetch failed | card_id={card.id} "
                f"attempt={card.information_counter + 1} error={exc}"
            )

            card.information_counter += 1
            card.check_again_on = timezone.now() + timedelta(minutes=RETRY_DELAY_MINUTES)

            card.save(update_fields=[
                "information_counter",
                "check_again_on"
            ])

