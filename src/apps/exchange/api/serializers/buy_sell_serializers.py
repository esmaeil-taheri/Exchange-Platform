from rest_framework import serializers

from apps.exchange.services.exchange_services import ExchangeService


class BuySerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, max_digits=12, decimal_places=4)
    aseet = serializers.ChoiceField(choices=['XAU18'], required=True)
    buy_from_wallet = serializers.BooleanField(default=False)

    def create(self, validated_data):
        return ExchangeService.buy_asset(
            asset=validated_data['aseet'],
            amount=validated_data['amount'],
            buy_from_wallet=validated_data['buy_from_wallet']
        )
