from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.notifications.selectors.notification_selector import NotificationSelector
from apps.notifications.api.serializers.notification_serializers import NotificationAsReadSerializer, NotificationListResponseSerializer
from apps.core.pagination import StandardResultsSetPagination


@extend_schema_view(
    get=extend_schema(
        summary="List user notifications",
        tags=['Notifications'],
        description="Returns paginated notifications for the authenticated user.",
        responses=NotificationListResponseSerializer,
    )
)

class GetNotificationsListApiView(ListAPIView):
    serializer_class = NotificationListResponseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return NotificationSelector.get_notifications_by_user_id(
            user_id=self.request.user.id
        )
    

class ReadNotificationApiView(APIView):
    @extend_schema(
        summary="Mark a notification as read",
        tags=['Notifications'],
        request=None,
        responses={204: None},
    )

    def get(self, request, notif_id: int, *args, **kwargs):
        serializer = NotificationAsReadSerializer(data={}, context={
            'request': request,
            'notif_id': notif_id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)