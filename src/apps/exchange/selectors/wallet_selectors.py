
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
    def get_user_balance_under_customer_lock(user_id: int, wallet_type: str):
        """
        Sum the customer's verified ledger entries for one wallet type.

        This does NOT lock anything, and previously only appeared to: Django
        drops `select_for_update()` when the queryset is resolved through
        `.aggregate()`, so the emitted SQL was a plain `SELECT SUM(...)` with no
        locking clause at all. The name has been corrected to say what actually
        guarantees correctness.

        The real serialization point is the `Customer` row lock. Every path that
        DEBITS a wallet — `ExchangeService.buy_asset`, `ExchangeService.sell_asset`
        and `SettlementService.initiate_withdrawal_request` — takes
        `Customer.objects.select_for_update()` first and holds it across both the
        balance check and the debit, so two concurrent debits of one customer
        cannot interleave. Callers that debit MUST hold that lock.

        A real row lock here would be worse, not better: it would make the
        request path take Customer -> Wallet while the settlement workers take
        Transaction -> Wallet -> Customer (the FK on their credit insert), and
        those two orders deadlock. The settlement workers only ever credit, so
        an unlocked read is safe for them.
        """
        return Wallet.objects.filter(
            customer__user_id=user_id,
            wallet_type=wallet_type,
            is_verified=True,
        ).aggregate(total=Sum('amount'))['total'] or 0