from django.db import models
from django.conf import settings


class Notification(models.Model):

    TYPE_CHOICES = [
        ('public', 'Public'),
        ('user', 'User Specific'),
        ('action', 'Action Based'),
    ]

    template = models.ForeignKey(
        'notifications.NotificationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        related_name='notifications'
    )

    title = models.CharField(max_length=255)
    body = models.TextField()

    category = models.CharField(max_length=50, db_index=True)
    severity = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.type} - {self.title}"
