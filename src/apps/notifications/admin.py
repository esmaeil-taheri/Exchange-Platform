from django.contrib import admin

from .models import Notification, NotificationTemplate, UserNotificationStatus

admin.site.register(Notification)
admin.site.register(NotificationTemplate)
admin.site.register(UserNotificationStatus)