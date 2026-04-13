from rest_framework import serializers

from apps.customers.services.kyc_services import KycService


class CustomerIdentityInquirySerializer(serializers.Serializer):
    national_id = serializers.CharField(max_length=10, min_length=10)
    first_name = serializers.CharField(max_length=50, min_length=3)
    last_name = serializers.CharField(max_length=50, min_length=3)
    birthday= serializers.CharField(max_length=10, min_length=10, )

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        return KycService.get_customer_identity_inquiry(
            user=user, first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            national_id=validated_data['national_id'],
            birthday_date=validated_data['birthday']
        )
    

class CustomerKycStatusSerializer(serializers.Serializer):
    kyc_level = serializers.CharField()
    is_verified = serializers.BooleanField()


class CustomerKycStatusResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    detail = CustomerKycStatusSerializer()


class CustomerIdentityInquiryResponseSerializer(serializers.Serializer):
    message = serializers.CharField()