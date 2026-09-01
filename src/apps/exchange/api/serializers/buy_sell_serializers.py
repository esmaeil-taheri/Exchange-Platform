from rest_framework import serializers

from apps.exchange.services.exchange_services import ExchangeService
from apps.exchange.models.transaction import Transaction
from apps.core.utils.idempotency_utils import extract_idempotency_key


class BuySerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, max_digits=13, decimal_places=4)
    aseet = serializers.ChoiceField(choices=['XAU18'], required=True)
    buy_from_wallet = serializers.BooleanField(default=False)

    def validate(self, validated_data):
        if not validated_data['buy_from_wallet']:
            if validated_data['amount'] < 100000 or validated_data['amount'] > 100000000:
                raise serializers.ValidationError('افزایش اعتبار کیف پول نمیتواند کمتر از 100 هزار تومان و بیشتر از 100 میلیون باشد')
            
        return validated_data


    def create(self, validated_data):
        request = self.context['request']
        return ExchangeService.buy_asset(
            request=request,
            asset=validated_data['aseet'],
            amount=validated_data['amount'],
            buy_from_wallet=validated_data['buy_from_wallet'],
            idempotency_key=extract_idempotency_key(request),
        )


class IRTTransactionListSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    wallet_type = serializers.CharField()
    desc = serializers.CharField()
    verified_at = serializers.IntegerField()
    created_at = serializers.IntegerField()
 

class XAU18TransactionListSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=4)
    wallet_type = serializers.CharField()
    desc = serializers.CharField()
    verified_at = serializers.IntegerField()
    created_at = serializers.IntegerField()


class InvoiceListSerializer(serializers.ModelSerializer):

    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    wallet_name = serializers.CharField(source='wallet.wallet_type', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'status',
            'amount',
            'fee_amount',
            'fee_irt',
            'unit_price_irt',
            'total_price_irt',
            'currency_symbol',
            'wallet_name',
            'created_at',
            'processed_at'
        ]

class SellSerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, max_digits=13, decimal_places=4)
    aseet = serializers.ChoiceField(choices=['XAU18'], required=True)
    card_withdaraw = serializers.BooleanField(default=False)
    bank_card_id = serializers.IntegerField(required=False)

    def create(self, validated_data):
        request = self.context['request']
        return ExchangeService.sell_asset(
            request=request,
            asset=validated_data['aseet'],
            amount=validated_data['amount'],
            card_withdaraw=validated_data['card_withdaraw'],
            bank_card_id=validated_data.get('bank_card_id'),
            idempotency_key=extract_idempotency_key(request),
        )
    
    def validate(self, attrs):
        if attrs.get('card_withdaraw') and not attrs.get('bank_card_id'):
            raise serializers.ValidationError("bank_card_id is required when card_withdaraw is True.")
        return attrs
