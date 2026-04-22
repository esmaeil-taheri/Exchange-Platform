from apps.exchange.models.wallet import Wallet


class WalletService:

    @staticmethod
    def create_wallet_entry(customer, currency, amount, desc, ip, timestamp):

        return Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            desc=desc,
            amount=amount,
            created_at=timestamp,
            verified_at=timestamp,
            ip=ip,
            is_verified=True
        )