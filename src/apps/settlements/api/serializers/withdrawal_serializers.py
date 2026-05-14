from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.settlements.models.withdrawal import Withdrawal
from apps.settlements.services.settlement_services import SettlementService


class WithdrawalBaseMessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal list representation."""

    created_at_jalali = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()

    class Meta:
        model = Withdrawal
        fields = [
            'id',
            'bank_name',
            'card_number',
            'amount',
            'status',
            'track_id',
            'settlement_method',
            'created_at_jalali'
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField)
    def get_bank_name(self, obj):
        """Get bank name from card."""
        if obj.card:
            return obj.card.bank_name
        return "Unknown"

    @extend_schema_field(serializers.CharField)
    def get_card_number(self, obj):
        """Get masked card number."""
        if obj.card:
            return obj.card.card_number
        return "Unknown"
    
    @extend_schema_field(serializers.CharField)
    def get_created_at_jalali(self, obj) -> str:
        return obj.created_at_jalali


class WithdrawalDetailSerializer(serializers.Serializer):
    message = serializers.CharField()
    data = WithdrawalSerializer()


class WithdrawSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        required=True,
        help_text="Amount to be deposited in the user's account."
    )
    card_id = serializers.IntegerField(required=True)

    def create(self, validated_data):
        request = self.context.get('request')
        return SettlementService.initiate_withdrawal_request(
            validated_data['amount'], 
            validated_data['card_id'],
            request
        )

    def validate(self, validated_data):

        if validated_data['amount'] < 100000 or validated_data['amount'] > 100000000:
            raise serializers.ValidationError('مبلغ برداشت نمیتواند کمتر از 100 هزار تومان و بیشتر از 100 میلیون باشد')
            
        return validated_data