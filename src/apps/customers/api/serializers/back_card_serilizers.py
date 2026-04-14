from rest_framework import serializers

from drf_spectacular.utils import extend_schema_field

from apps.customers.services.back_card_services import BankCardService
from apps.customers.models.bank_card import BankCard
from apps.core.utils.validation_utils import validate_iranian_card_number


class CreateBankCardSerializer(serializers.Serializer):
    card_number = serializers.CharField(min_length=16, max_length=16)

    def validate(self, data):
        card_number = validate_iranian_card_number(data['card_number'])
        if not card_number:
            raise serializers.ValidationError('کارت معتبر نیست')
        return data

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        return BankCardService.create_card(
            customer=user.customer_profile, 
            card_number=validated_data['card_number']
        )


class BankCardResponseSerializer(serializers.ModelSerializer):

    user_fullname = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField())
    def get_user_fullname(self, obj):
        return obj.customer.full_name
    
    class Meta:
        model=BankCard
        fields = [
            'id', 'bank_name', 'card_number', 
            'user_fullname', 'is_verified'
        ]


class DeleteBankCardSerializer(serializers.Serializer):

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        card_id = self.context['card_id']

        return BankCardService.delete_bank_card(
            customer=user.customer_profile,
            card_id=card_id
        )
