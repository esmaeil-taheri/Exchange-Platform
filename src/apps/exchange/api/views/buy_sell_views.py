from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.customers.api.permissions.customer_permisions import IsCustomerAuthenticated
from apps.core.exceptions.open_api import ErrorSerializer
from apps.exchange.api.serializers.buy_sell_serializers import BuySerializer


class BuyApiView(APIView):
    
    permission_classes = [IsAuthenticated, IsCustomerAuthenticated]

    @extend_schema(
        summary="Buy Asset",
        tags=['Exchange'],
        request=BuySerializer,
        responses={
            200: OpenApiResponse(

                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "price_buy": 17332900,
                            "price_sell": 17332900,
                            "difference_price_buy": -100,
                            "difference_price_sell": -100,
                            "lower_amounts": {
                                "buy_toman": 303356,
                                "sell_toman": 476655,
                                "buy_gold": 0.015,
                                "sell_gold": 0.03
                            },
                            "system_balance_amount": 10000,
                            "timestamp": 1776435240
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

    def post(self, request, *args, **kwargs):
        serializer = BuySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(
            data,
            status=status.HTTP_201_CREATED
        )
