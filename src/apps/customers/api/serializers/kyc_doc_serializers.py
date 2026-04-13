from rest_framework import serializers

from apps.customers.services.kyc_services import KycService


class CustomerKycUploadSerializer(serializers.Serializer):
    national_card_image = serializers.ImageField()

    def validate_national_card_image(self, image):
        if image.size > 2 * 1024 * 1024:
            raise serializers.ValidationError('حجم تصویر نباید بیشتر از ۲ مگابایت باشد')
        
        if image.content_type not in ["image/jpeg", "image/png"]:
            raise serializers.ValidationError("فرمت تصویر نامعتبر است")
        
        return image
    
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        return KycService.submit_customer_kyc_document(
            user=user,
            doc=validated_data['national_card_image']
        )


class CustomerKycUploadResponseSerializer(serializers.Serializer):
    message = serializers.CharField()