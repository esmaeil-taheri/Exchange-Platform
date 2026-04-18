from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse


from apps.exchange.selectors.price_selectors import PriceSelector
from apps.exchange.api.serializers.price_serializers import PriceLogSerializer
from apps.core.exceptions.open_api import ErrorSerializer


class GetBuySellPriceApiView(APIView):

    @extend_schema(
        summary="Get Buy/Sell Price",
        tags=['Exchange'],
        request=None,
        responses={
            200: OpenApiResponse(
                response=PriceLogSerializer,

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

    def get(self, request, *args, **kwargs):
        response = PriceSelector.get_buy_sell_price()
        serializer = PriceLogSerializer(response)
        return Response(
            serializer.data, 
            status=status.HTTP_200_OK
        )