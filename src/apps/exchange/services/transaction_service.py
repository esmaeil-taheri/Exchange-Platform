from decimal import Decimal
from apps.exchange.models.transaction import Transaction


class TransactionService:

    @staticmethod
    def create_buy_transaction(customer, currency, wallet, deposit_method, calculated_price, ip, timestamp):

        return Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet,
            amount=calculated_price['data']['gold_amount'],
            fee_amount = (
                Decimal(calculated_price['data']['fee_toman']) /
                Decimal(calculated_price['data']['price_per_gram'])
            ).quantize(Decimal('0.0001')),
            fee_irt=calculated_price['data']['fee_toman'],
            unit_price_irt=calculated_price['data']['price_per_gram'],
            total_price_irt=calculated_price['data']['total_amount'],
            ip=ip,
            withdraw_method=Transaction.WITHDRAWTYPES[0][0],
            deposit_method=deposit_method,
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            created_at=timestamp
        )
    
    @staticmethod
    def create_sell_transaction(customer, currency, wallet, withdraw_method, calculated_price, ip, timestamp):

        return Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet,
            amount=calculated_price['data']['gold_amount'],
            fee_amount = (
                Decimal(calculated_price['data']['fee_toman']) /
                Decimal(calculated_price['data']['price_per_gram'])
            ).quantize(Decimal('0.0001')),
            fee_irt=calculated_price['data']['fee_toman'],
            unit_price_irt=calculated_price['data']['price_per_gram'],
            total_price_irt=calculated_price['data']['total_amount'],
            ip=ip,
            withdraw_method=withdraw_method,
            deposit_method=Transaction.DEPOSITTYPES[0][0],
            transaction_type=Transaction.TRANSACTIONTYPES[1][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            created_at=timestamp
        )
    