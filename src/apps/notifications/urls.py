from django.urls import path

from apps.notifications.api.views.notification_views import GetNotificationsListApiVie, ReadNotificationApiView

urlpatterns = [
    path('', GetNotificationsListApiVie.as_view(), name='notifications-list'),
    path('read/<int:notif_id>/', ReadNotificationApiView.as_view(), name='read-notification')
]
