from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.accounts.api.serializers.user_serializers import (
    MessageResponseSerializer, Change2FAStatusSerializer, 
    LoginRegisterSerializer, LoginRegisterVerifySerializer,
    OtpSendResponseSerializer, LoginRegisterVerifyResponseSerializer, 
    TwoFaUriSerializer, Verify2faAccessSerializer
)
from apps.core.exceptions.open_api import ErrorSerializer
from apps.accounts.services.user_services import UserService
from apps.core.decorators.rate_limit import rate_limit


class LoginRegisterApiView(APIView):
    """Handle user login."""

    @extend_schema(
        summary="Login with OTP",
        tags=['Accounts'],
        request=LoginRegisterSerializer,
        description="Send OTP to user's phone",
        responses={
            200: OpenApiResponse(
                response=OtpSendResponseSerializer,

                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "message": "code sent successfully",
                            "data": {
                                "phone_number": "09121110022"
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="RegistrationDisabled",
                        value={"detail": "Registration is currently disabled."}
                    )
                ]
            )
        }
    )

    @rate_limit(scope='otp_send_ip',    limit=5, window=600, key='ip')
    @rate_limit(scope='otp_send_phone', limit=3, window=600, key='phone', phone_field='phone_number')
    def post(self, request, *args, **kwargs):
        serializer = LoginRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.save()

        return Response(
            data,
            status=status.HTTP_200_OK
        )
        

class LoginRegisterVerifyApiView(APIView):
    """Handle user login verification."""

    @extend_schema(
        summary="Login Verify OTP",
        tags=['Accounts'],
        request=LoginRegisterVerifySerializer,
        description="Authenticate user and returns JWT token",
        responses={
            200: OpenApiResponse(
                response=LoginRegisterVerifyResponseSerializer,
                description="Login Was Successfull.",
                examples=[
                    OpenApiExample(
                        name="Successfull Login",
                        value={
                            "message": "Login Was Successfull",
                            "data": {
                                "access_token": "eyJhbGc...",
                                "refresh_token": "eyJhbGc...",
                                "first_time_login": True,
                                "two_fa_enabled": False
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="Not Authenticated",
                        value={"detail": "Authentication credentials were not provided."}
                    )
                ]
            )
        }
    )

    @rate_limit(scope='otp_verify_ip', limit=10, window=600, key='ip')
    def post(self, request, *args, **kwargs):
        serializer = LoginRegisterVerifySerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.save()

        return Response(
            data, status=status.HTTP_200_OK
        )


class Get2FAUriApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get 2FA setup URI",
        tags=['Accounts'],
        description="Returns the secret and URI needed to configure 2FA in authenticator apps.",
        responses=TwoFaUriSerializer
    )
    def get(self, request, *args, **kwargs):
        data = UserService.setup_2fa(request=request)
        serializer = TwoFaUriSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class Verify2FAAccessApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
    summary="Send OTP for Change 2FA Status",
    tags=['Accounts'],
    description="Send OTP to user's phone to change 2fa status",
    request=Verify2faAccessSerializer,
        responses={
            200: OpenApiResponse(
                response=OtpSendResponseSerializer,
                description="Login Was Successfull.",
                examples=[
                    OpenApiExample(
                        name="Action Was Successfull",
                        value={
                            "message": "code sent successfully",
                            "data": {
                                "phone_number": "09121110022"
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="Not Authenticated",
                        value={"detail": "Authentication credentials were not provided."}
                    )
                ]
            )
        }
    )
    
    @rate_limit(scope='2fa_otp_send', limit=3, window=600, key='user')
    def post(self, request, *args, **kwargs):
        serializer = Verify2faAccessSerializer(data={}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        return Response(
            data, status=status.HTTP_200_OK
        )


class Change2FAStatusApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
    summary="Change 2FA Status",
    tags=['Accounts'],
    description="Enable/Disable 2FA",
    request=Change2FAStatusSerializer,
        responses={
            200: OpenApiResponse(
                response=MessageResponseSerializer,
                description="Login Was Successfull.",
                examples=[
                    OpenApiExample(
                        name="Action Was Successfull",
                        value={
                            "message": "Status changed successfully"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="Not Authenticated",
                        value={"detail": "Authentication credentials were not provided."}
                    )
                ]
            )
        }
    )
    
    def post(self, request, *args, **kwargs):
        serializer = Change2FAStatusSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = serializer.save()

        serializer = MessageResponseSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.data, status=status.HTTP_200_OK
        )