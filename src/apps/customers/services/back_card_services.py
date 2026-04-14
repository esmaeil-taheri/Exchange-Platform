from django.utils import timezone

from apps.customers.models.bank_card import BankCard
from apps.customers.models.customer import Customer
from apps.core.utils.validation_utils import detect_bank
from apps.customers.exceptions.bank_card_exceptions import BankCardAlreadyExists, BankCardNotFound


class BankCardService:
    @staticmethod
    def create_card(*, customer: Customer, card_number: str) -> dict:

        card_exsists = BankCard.objects.filter(
            card_number=card_number, customer=customer, is_show=True
        ).exists()
        if card_exsists:
            raise BankCardAlreadyExists('کارت بانکی قبلا ثبت شده')
        
        card_exsists = BankCard.objects.filter(
            card_number=card_number, is_show=True).exists()
        if card_exsists:
            raise BankCardAlreadyExists('کارت بانکی قبلا ثبت شده')

        bank_name = detect_bank(card_number=card_number)
        card = BankCard.objects.create(
            customer=customer,
            bank_name=bank_name['bank_title'],
            card_number=card_number,
            check_again_on=timezone.now()

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
            raise BankCardNotFound('کارت بانکی یافت نشد')

        card.is_show = False
        card.save(update_fields=['is_show'])

        return True