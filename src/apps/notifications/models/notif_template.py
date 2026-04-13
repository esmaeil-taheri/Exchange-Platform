from django.db import models


class NotificationTemplate(models.Model):

    code = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()  
    category = models.CharField(max_length=50, db_index=True) 
    severity = models.IntegerField(default=1) 

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"

    def __str__(self):
        return self.code
