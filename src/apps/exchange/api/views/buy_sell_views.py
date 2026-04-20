from jsonschema import ValidationError
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter

from apps.customers.api.permissions.customer_permisions import IsCustomerAuthenticated
from apps.core.exceptions.open_api import ErrorSerializer
from apps.exchange.api.serializers.buy_sell_serializers import BuySerializer, IRTTransactionListSerializer, XAU18TransactionListSerializer
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.core.pagination import StandardResultsSetPagination


class GetBalanceApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get User Wallets",
        tags=['Exchange'],
        parameters=[
            OpenApiParameter(
                name='wallet_type', 
                description='The Wallet type', 
                required=False, enum=['irt', 'xau18']
            ),
        ],
        responses={
            200: OpenApiResponse(
                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "wallets": [
                                {
                                    "wallet_type": "XAU18",
                                    "balance": 0.015,
                                    "equivalent_balance": 260000,
                                    "equivalent_currency": "IRT"
                                },
                                {
                                    "wallet_type": "IRT",
                                    "balance": 260000,
                                    "equivalent_balance": 0.015,
                                    "equivalent_currency": "XAU18"
                                }
                            ]
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

        wallet_type = request.query_params.get("wallet_type")

        data = WalletSelector.get_user_balance(
            user_id=request.user.id,
            wallet_type=wallet_type
        )

        return Response(
            {   "message": "Success",
                "data": data
            },
            status=status.HTTP_200_OK
        )


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


@extend_schema(
    summary="Get User Transaction List",
    tags=["Exchange"],
    parameters=[
        OpenApiParameter(
            name="wallet_type",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            enum=["IRT", "XAU18"],
            description="Wallet type"
        ),
    ],
    responses={
        200: IRTTransactionListSerializer(many=True),
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
class GetTransactionListApiview(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        wallet_type = self.request.GET.get('wallet_type')

        if wallet_type == 'IRT':
            return IRTTransactionListSerializer

        if wallet_type == 'XAU18':
            return XAU18TransactionListSerializer

        raise ValidationError({"detail": "wallet_type must be one of: IRT, XAU18"})

    def get_queryset(self):
        wallet_type = self.request.GET.get('wallet_type')

        if wallet_type == 'IRT':
            return WalletSelector.get_wallets_by_user_id(
                user_id=self.request.user.id,
                wallet_type='irt'
            )

        if wallet_type == 'XAU18':
            return WalletSelector.get_wallets_by_user_id(
                user_id=self.request.user.id,
                wallet_type='xau'
            )

        raise ValidationError({"detail": "wallet_type must be one of: IRT, XAU18"})
