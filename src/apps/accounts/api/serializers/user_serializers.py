from rest_framework import serializers

from apps.accounts.services.user_services import UserService


class LoginRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(min_length=11, max_length=11)

    def create(self, validated_data):

        return UserService.login_register(
            phone_number=validated_data['phone_number']
        )


class OtpSendDataSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class OtpSendResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    data = OtpSendDataSerializer()


class LoginRegisterVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(min_length=11, max_length=11)
    code = serializers.CharField(min_length=6, max_length=6)

    def create(self, validated_data):
        request = self.context["request"]
        
        return UserService.login_register_verify(
            phone_number=validated_data['phone_number'],
            code=validated_data['code'],
            request=request
        )
    

class TokenDetailSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    two_fa_enabled = serializers.BooleanField()
    first_time_login = serializers.BooleanField()


class LoginRegisterVerifyResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    data = TokenDetailSerializer()


class TwoFaUriSerializer(serializers.Serializer):
    setup_key = serializers.CharField()
    uri = serializers.CharField()


class Verify2faAccessSerializer(serializers.Serializer):
    
    def create(self, validated_data):
        request = self.context['request']
        phone_number = request.user.phone_number

        return UserService.send_two_factor_otp(
            phone_number=phone_number
        )


class Change2FAStatusSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)
    authenticator_code = serializers.CharField(min_length=6, max_length=6)
    is_2fa = serializers.BooleanField()

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        return UserService.two_fa_change_status(
            user=user,
            code=validated_data['code'],
            authenticator_code=validated_data['authenticator_code'],
            is_2fa=validated_data['is_2fa']
        )


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()