from apps.exchange.models.wallet import Wallet


class WalletService:

    @staticmethod
    def create_wallet_entry(customer, wallet_type, amount, desc, ip, timestamp):

        return Wallet.objects.create(
            customer=customer,
            wallet_type=wallet_type,
            desc=desc,
            amount=amount,
            created_at=timestamp,
            verified_at=timestamp,
            ip=ip,
            is_verified=True
        )