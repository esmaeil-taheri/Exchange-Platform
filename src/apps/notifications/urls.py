from django.urls import path

from apps.notifications.api.views.notification_views import GetNotificationsListApiView, ReadNotificationApiView

urlpatterns = [
    path('', GetNotificationsListApiView.as_view(), name='notifications-list'),
    path('read/<int:notif_id>/', ReadNotificationApiView.as_view(), name='read-notification')
]
