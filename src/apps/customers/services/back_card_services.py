from django.utils import timezone

from apps.customers.models.bank_card import BankCard
from apps.customers.models.customer import Customer
from apps.core.utils.validation_utils import detect_bank
from apps.customers.exceptions.bank_card_exceptions import BankCardAlreadyExists, BankCardNotFound
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


class BankCardService:
    @staticmethod
    def create_card(*, customer: Customer, card_number: str) -> dict:
        masked = f"{card_number[:6]}****{card_number[-4:]}"

        card_exists = BankCard.objects.filter(
            card_number=card_number, customer=customer, is_show=True
        ).exists()
        if card_exists:
            logger.warning(
                f"Bank card add rejected — duplicate for this customer | "
                f"customer_id={customer.id} card={masked}"
            )
            raise BankCardAlreadyExists('کارت بانکی قبلا ثبت شده')

        card_exists = BankCard.objects.filter(
            card_number=card_number, is_show=True).exists()
        if card_exists:
            logger.warning(
                f"Bank card add rejected — card already registered by another customer | "
                f"customer_id={customer.id} card={masked}"
            )
            raise BankCardAlreadyExists('کارت بانکی قبلا ثبت شده')

        bank_name = detect_bank(card_number=card_number)
        card = BankCard.objects.create(
            customer=customer,
            bank_name=bank_name['bank_title'],
            card_number=card_number,
            check_again_on=timezone.now()
        )

        logger.info(
            f"Bank card added | customer_id={customer.id} "
            f"card_id={card.id} bank={bank_name['bank_title']} card={masked}"
        )
        return card

    @staticmethod
    def delete_bank_card(*, customer: Customer, card_id: int):
        card = BankCard.objects.filter(
            customer=customer,
            id=card_id,
            is_show=True
        ).first()

        if not card:
            logger.warning(
                f"Bank card delete failed — not found | "
                f"customer_id={customer.id} card_id={card_id}"
            )
            raise BankCardNotFound('کارت بانکی یافت نشد')

        card.is_show = False
        card.save(update_fields=['is_show'])

        logger.info(
            f"Bank card soft-deleted | customer_id={customer.id} card_id={card_id}"
        )
        return True