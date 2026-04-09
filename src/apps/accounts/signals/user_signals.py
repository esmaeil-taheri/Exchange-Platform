from django.core.mail import send_mail
from django.dispatch import receiver

from apps.accounts.services.user_services import user_registered
from django.conf import settings


@receiver(user_registered)
def send_welcome_email(sender, user, **kwargs):
    """Send a welcome email after successful registration."""

    subject = "Welcome to Our Platform!"
    message = f"""
        Hi {user.username},

        Welcome to our platform! We’re glad to have you onboard.

        Best regards,
        Your Team
    """
    print(subject,'\n', message)
