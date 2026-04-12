from django.db import transaction
from django.utils import timezone

from apps.notifications.models.notif_template import NotificationTemplate
from apps.notifications.models.notification import Notification
from apps.notifications.models.notif_status import UserNotificationStatus
from apps.notifications.exceptions.notification_exceptions import NotificationAlreadyRead, NotificationNotFound

class NotificationService:

    @staticmethod
    def create_notification_from_template(template_code, user=None, context=None):
        context = context or {}

        template = NotificationTemplate.objects.get(code=template_code)

        body = template.body
        for key, value in context.items():
            body = body.replace(f'{{{{{key}}}}}', str(value))

        notif = Notification.objects.create(
            user=user,
            template=template,
            type='user' if user else 'public',
            title=template.title,
            body=body,
            category=template.category,
            severity=template.severity
        )

        if user:
            UserNotificationStatus.objects.create(
                user=user,
                notification=notif,
                is_read=False
            )

        return notif
    
    @staticmethod
    @transaction.atomic
    def mark_as_read(*, notif_id: int, user_id: int) -> bool:

        try:
            status = UserNotificationStatus.objects.select_for_update().get(
                user_id=user_id,
                notification_id=notif_id
            )
        except UserNotificationStatus.DoesNotExist:
            raise NotificationNotFound("پیام یافت نشد")

        if status.is_read:
            raise NotificationAlreadyRead("پیام قبلاً خوانده شده است")

        status.is_read = True
        status.read_at = timezone.now()
        status.save(update_fields=["is_read", "read_at"])

        return True
    
        