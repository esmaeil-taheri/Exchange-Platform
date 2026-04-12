from rest_framework import serializers

from apps.notifications.models.notification import Notification
from apps.notifications.services.notification_services import NotificationService


class NotificationListResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'body',
        ]

class NotificationAsReadSerializer(serializers.Serializer):

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        notif_id = self.context['notif_id']

        return NotificationService.mark_as_read(user_id=user.id, notif_id=notif_id)
