from rest_framework import serializers

from apps.payments.services.payments_services import PaymentService
from apps.core.utils.idempotency_utils import extract_idempotency_key


class BaseMessageSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)


class ZarinpalCallbackSerializer(serializers.Serializer):
    gateway_track_id = serializers.CharField(
        required=True,
        help_text="Gateway tracking ID returned by Zarinpal after payment."
    )

    def create(self, validated_data):
        request = self.context.get('request')
        return PaymentService.handle_zarinpal_callback(validated_data['gateway_track_id'], request)
    

class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        required=True,
        help_text="Amount to be deposited in the user's account."
    )

    def create(self, validated_data):
        request = self.context.get('request')
        return PaymentService.initiate_deposit(
            validated_data['amount'],
            request,
            idempotency_key=extract_idempotency_key(request),
        )


    def validate(self, validated_data):

        if validated_data['amount'] < 100000 or validated_data['amount'] > 100000000:
            raise serializers.ValidationError('افزایش اعتبار کیف پول نمیتواند کمتر از 100 هزار تومان و بیشتر از 100 میلیون باشد')
            
        return validated_data