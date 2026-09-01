from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.payments.api.serializers.payments_serializers import BaseMessageSerializer, DepositSerializer, ZarinpalCallbackSerializer
from apps.core.exceptions.open_api import ErrorSerializer
from apps.core.decorators.rate_limit import rate_limit
from apps.core.utils.openapi_params import IDEMPOTENCY_KEY_PARAMETER


class ZarinpalCallbackApiView(APIView):

    @extend_schema(
        summary="Zarinpal payment callback",
        tags=['Payments'],
        description="Endpoint used to receive the gateway_track_id after the user returns from the Zarinpal payment gateway.",
        request=ZarinpalCallbackSerializer,
        responses={
            200: OpenApiResponse(
                response=BaseMessageSerializer,
                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "message": "Payment was successful"
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
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            )
        }
    )
    @rate_limit(scope='zarinpal_callback_ip', limit=20, window=60, key='ip')
    def post(self, request, *args, **kwargs):
        serializer = ZarinpalCallbackSerializer(data=self.request.data, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)


class DepositApiView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Deposit funds",
        tags=['Payments'],
        description="Endpoint used to deposit funds into the user's account.",
        request=DepositSerializer,
        parameters=[IDEMPOTENCY_KEY_PARAMETER],
        responses={
            200: OpenApiResponse(
                response=BaseMessageSerializer,
                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "message": "Payment was successful"
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
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            )
        }
    )
    @rate_limit(scope='deposit_user', limit=3, window=300, key='user')
    def post(self, request, *args, **kwargs):
        serializer = DepositSerializer(data=self.request.data, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)