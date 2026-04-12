from django.db import models

from django.conf import settings

class UserNotificationStatus(models.Model):
    """
    وضعیت خوانده‌شدن هر اعلان برای هر کاربر.
    فقط زمانی رکورد ساخته می‌شود که کاربر نوتیف را بخواند یا وارد لیست unread شود.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_statuses'
    )

    notification = models.ForeignKey(
        'notifications.Notification',
        on_delete=models.CASCADE,
        related_name='user_statuses'
    )

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'notification')
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.notification_id} - {self.is_read}"
