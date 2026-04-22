
from apps.exchange.models import Wallet
from apps.exchange.selectors.price_selectors import PriceSelector

from django.db.models import Sum


class WalletSelector:

    @staticmethod
    def get_user_balance(user_id: int, wallet_type: str | None = None) -> list:

        current_price = PriceSelector.get_xau18_current_price()
        price = current_price['price']

        irt_balance = Wallet.objects.filter(
            customer__user_id=user_id,
            wallet_type='irt',
            is_verified=True
        ).aggregate(balance=Sum('amount'))['balance'] or 0

        xau_balance = Wallet.objects.filter(
            customer__user_id=user_id,
            wallet_type='xau',
            is_verified=True
        ).aggregate(balance=Sum('amount'))['balance'] or 0

        all_wallets = {
            "xau": {
                "wallet_type": "XAU18",
                "balance": round(xau_balance, 6),
                "equivalent_balance": round(xau_balance * price, 6),
                "equivalent_currency": "IRT"
            },
            "irt": {
                "wallet_type": "IRT",
                "balance": irt_balance,
                "equivalent_balance": round(irt_balance / price, 6) if price else 0,
                "equivalent_currency": "XAU18"
            }
        }

        if wallet_type is None:
            return list(all_wallets.values())

        wallet_type = wallet_type.lower()
        if wallet_type == "xau18":
            wallet_type = "xau"

        return [all_wallets[wallet_type]]

    @staticmethod
    def get_wallets_by_user_id(user_id: int, wallet_type: str):
        return Wallet.objects.filter(
            customer__user_id=user_id, wallet_type=wallet_type, is_verified=True,
            ).only(
            'id', 'amount',  'wallet_type', 'desc', 'verified_at', 'created_at'
        )
    
    @staticmethod
    def get_user_balance_for_update(user_id: int, wallet_type: str):

        wallets = (
            Wallet.objects
            .select_for_update()
            .filter(
                customer__user_id=user_id,
                wallet_type=wallet_type,
                is_verified=True
            )
        )

        balance = wallets.aggregate(total=Sum('amount'))['total'] or 0
        return balance