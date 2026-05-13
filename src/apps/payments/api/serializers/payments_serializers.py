from rest_framework import serializers

from apps.payments.services.payments_services import PaymentService


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
    
