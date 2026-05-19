from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework import status
# from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse, OpenApiParameter

from apps.settlements.models.withdrawal import Withdrawal
from apps.settlements.selectors.withdrawal_selectors import WithdrawalSelectors
from apps.settlements.api.serializers.withdrawal_serializers import WithdrawSerializer, WithdrawalBaseMessageSerializer, WithdrawalDetailSerializer, WithdrawalSerializer
from apps.core.pagination import StandardResultsSetPagination
from apps.core.exceptions.open_api import ErrorSerializer
from apps.core.decorators.rate_limit import rate_limit


@extend_schema_view(
    get=extend_schema(
        summary="List user withdrawals",
        tags=['Settlements'],
        description="Returns paginated list of withdrawals for the authenticated customer.",
        parameters=[
            OpenApiParameter(
                name='status',
                description='Filter by withdrawal status (pending, sent_to_bank, completed, failed, cancelled)',
                required=False,
                enum=['pending', 'sent_to_bank',
                      'completed', 'failed', 'cancelled']
            ),
            OpenApiParameter(
                name='ordering',
                description='Order results by field (e.g., -process_time for newest first)',
                required=False
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=WithdrawalSerializer(many=True),
                description="Successful retrieval of withdrawals",
                examples=[
                    OpenApiExample(
                        name="Successful withdrawal list",
                        value={
                            "id": 1,
                            "bank_name": "بانک ملی",
                            "card_number": "1234567890123456",
                            "amount": 1000000,
                            "status": "completed",
                            "settlement_method": "پایا",
                            "track_id": "6e8998b8-ebfe-4ef8-abe9-437b5c6c3dc2",
                            "created_at_jalali": "2026-05-14T10:30:00Z"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 500)"
            )
        }
    )
)
class WithdrawalListApiView(ListAPIView):
    """
    List all withdrawals for the authenticated customer.

    Supports filtering by status and custom ordering.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalSerializer
    pagination_class = StandardResultsSetPagination
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['process_time', 'amount', 'status']
    ordering = ['-process_time']

    def get_queryset(self):
        """Return withdrawals for the authenticated customer."""
        customer = self.request.user.customer_profile
        return WithdrawalSelectors.get_customer_withdrawals(customer)


@extend_schema_view(
    get=extend_schema(
        summary="Get withdrawal details",
        tags=['Settlements'],
        description="Returns detailed information about a specific withdrawal.",
        responses={
            200: OpenApiResponse(
                response=WithdrawalDetailSerializer,
                description="Successful retrieval of withdrawal details",
                examples=[
                    OpenApiExample(
                        name="Successful withdrawal details",
                        value={
                            "message": "success",
                            "data": {
                                "id": 1,
                                "bank_name": "بانک ملی",
                                "card_number": "1234567890123456",
                                "amount": 1000000,
                                "status": "completed",
                                "settlement_method": "پایا",
                                "track_id": "6e8998b8-ebfe-4ef8-abe9-437b5c6c3dc2",
                                "created_at_jalali": "2026-05-14T10:30:00Z"
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 404, 500)"
            )
        }
    )
)
class WithdrawalDetailApiView(RetrieveAPIView):
    """
    Retrieve detailed information about a specific withdrawal.

    Only allows access to withdrawals belonging to the authenticated customer.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'withdrawal_id'

    def get_queryset(self):
        """Return withdrawals for the authenticated customer only."""
        return WithdrawalSelectors.get_withdrawal_by_id(
            customer=self.request.user.customer_profile,
            withdrawal_id=self.kwargs['withdrawal_id']
        )
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            "message": "success",
            "data": serializer.data
        })


class CreateWithdrawalRequest(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create withdrawal request",
        tags=['Settlements'],
        description="Create a new withdrawal request for the authenticated customer.",
        request=WithdrawSerializer,
        responses={
            201: OpenApiResponse(
                response=WithdrawalBaseMessageSerializer,
                description="Withdrawal request created successfully",
                examples=[
                    OpenApiExample(
                        name="Successful withdrawal request",
                        value={
                            "message": "Withdrawal request created successfully"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Error response (400, 401, 403, 409, 500)",
                examples=[
                    OpenApiExample(
                        name="Validation Error",
                        value={
                            "detail": "Insufficient wallet balance."
                        }
                    )
                ]
            )
        }
    )

    @rate_limit(scope='withdrawal_user', limit=3, window=600, key='user')
    def post(self, request, *args, **kwargs):
        serializer = WithdrawSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(
            data,
            status=status.HTTP_200_OK
        )