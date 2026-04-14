from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse

from apps.customers.api.serializers.back_card_serilizers import BankCardResponseSerializer, CreateBankCardSerializer, DeleteBankCardSerializer
from apps.customers.api.permissions.customer_permisions import IsCustomerAuthenticated
from apps.core.pagination import StandardResultsSetPagination
from apps.customers.selectors.bank_card_selectors import BankCardSelectors
from apps.core.exceptions.open_api import ErrorSerializer


@extend_schema_view(
    get=extend_schema(
        summary="List user bank cards",
        tags=['Customers'],
        description="Returns paginated bank cards for the authenticated user.",
        responses=BankCardResponseSerializer,
    )
)
class BankCardListApiView(ListAPIView):
    permission_classes = [IsAuthenticated, IsCustomerAuthenticated]
    serializer_class = BankCardResponseSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return BankCardSelectors.get_user_bank_card_list(
            user_id=self.request.user.id
        )
    

class CreateBankCardApiView(APIView):

    permission_classes = [IsAuthenticated, IsCustomerAuthenticated]

    @extend_schema(
        summary="Create user bank card",
        tags=['Customers'],
        request=CreateBankCardSerializer,
        description="create bank card",
        responses={
            200: OpenApiResponse(
                response=BankCardResponseSerializer,

                examples=[
                    OpenApiExample(
                        name="Action was Successfull",
                        value={
                            "id": "integer",
                            "bank_name": "string",
                            "card_number": "string",
                            "user_fullname": "string",
                            "is_verified": "true"
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
        serializer = CreateBankCardSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        serializer = BankCardResponseSerializer(data)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
    

class DeleteBankCardApiView(APIView):

    permission_classes = [IsAuthenticated, IsCustomerAuthenticated]

    @extend_schema(
        summary="Delete bank card",
        tags=['Customers'],
        request=None,
        responses={
            204: None,
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="RegistrationDisabled",
                        value={"detail": "Inquiry is currently disabled."}
                    )
                ]
            ),
        },
    )

    def delete(self, request, card_id: int, *args, **kwargs):
        serializer = DeleteBankCardSerializer(
            data={},
            context={
                'request': request,
                'card_id': card_id
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )