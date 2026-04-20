from rest_framework import serializers

class LowerAmountsSerializer(serializers.Serializer):
    buy_toman = serializers.IntegerField()
    sell_toman = serializers.IntegerField()
    buy_gold = serializers.FloatField()
    sell_gold = serializers.FloatField()


class PriceLogSerializer(serializers.Serializer):
    price_buy = serializers.IntegerField()
    price_sell = serializers.IntegerField()
    difference_price_buy = serializers.IntegerField()
    difference_price_sell = serializers.IntegerField()
    lower_amounts = LowerAmountsSerializer()
    system_balance_amount = serializers.IntegerField()
    timestamp = serializers.IntegerField()


class PriceQueryParamsSerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, max_digits=12, decimal_places=4)
    unit = serializers.ChoiceField(choices=['XAU18', 'IRT'], required=True)
    transaction_type = serializers.ChoiceField(choices=["buy", "sell"], required=True)
