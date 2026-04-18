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