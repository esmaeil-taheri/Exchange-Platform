from django.dispatch import receiver

from apps.notifications.services.notification_services import NotificationService
from apps.accounts.services.user_services import login_detected

@receiver(login_detected)
def handle_user_login(sender, user, *args, **kwargs):
    NotificationService.create_notification_from_template(
        template_code='LOGIN_ALERT',
        user=user,
        context={
            'date': user.last_login.strftime('%Y-%m-%d %H:%M'),
            'ip': user.last_ip_address
        }
    )
