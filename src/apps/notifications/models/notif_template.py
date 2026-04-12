from django.db import models


class NotificationTemplate(models.Model):
    """
    قالب استفاده‌شونده برای اعلان‌های تکراری (اختیاری برای استفاده)
    مثلا: ORDER_CREATED, PRICE_CHANGED, WALLET_APPROVED, ...
    """

    code = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()  # می‌تواند شامل placeholders باشد: {{amount}}, {{price}}
    category = models.CharField(max_length=50, db_index=True)  # order, price, wallet, system
    severity = models.IntegerField(default=1)  # 1=low, 5=critical

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"

    def __str__(self):
        return self.code
