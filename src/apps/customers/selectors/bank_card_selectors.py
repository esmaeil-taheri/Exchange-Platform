from apps.customers.models.bank_card import BankCard
from apps.customers.exceptions.bank_card_exceptions import BankCardNotFound


class BankCardSelectors:
    @staticmethod
    def get_user_bank_card_list(*, user_id: int):
        cards = BankCard.objects.filter(
            customer__user_id=user_id,
            is_show=True
        )
        return cards
    
    @staticmethod
    def check_user_has_bank_card(user_id: int) -> bool:
        return BankCard.objects.filter(
            customer__user_id=user_id,
            is_show=True,
            is_verified=True

        ).exists()

    @staticmethod
    def get_customer_card_by_id(card_id: int, customer_id: int):
        try:
            card = BankCard.objects.get(
                id=card_id,
                customer__id=customer_id,
                is_show=True,
                is_verified=True
            )
            return card
        except BankCard.DoesNotExist:
            raise BankCardNotFound('کارت بانکی یافت نشد')