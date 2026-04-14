from apps.customers.models.bank_card import BankCard


class BankCardSelectors:
    @staticmethod
    def get_user_bank_card_list(*, user_id: int):
        cards = BankCard.objects.filter(
            customer__user_id=user_id,
            is_show=True
        )
        return cards