from rest_framework import serializers

from apps.exchange.services.exchange_services import ExchangeService


class BuySerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, max_digits=13, decimal_places=4)
    aseet = serializers.ChoiceField(choices=['XAU18'], required=True)
    buy_from_wallet = serializers.BooleanField(default=False)

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        return ExchangeService.buy_asset(
            user_id=user.id,
            asset=validated_data['aseet'],
            amount=validated_data['amount'],
            buy_from_wallet=validated_data['buy_from_wallet']
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