from apps.notifications.models.notification import Notification


class NotificationSelector:
    @staticmethod
    def get_notifications_by_user_id(*, user_id: int) -> dict:
        notifications = Notification.objects.prefetch_related('user_statuses').filter(
            user_id=user_id, 
            user_statuses__is_read=False
        )
        return notifications