from django.dispatch import receiver

from apps.accounts.services.user_services import user_registered
from apps.core.services.sms.sms_ir import SmsIrProvider


@receiver(user_registered)
def send_welcome_sms(sender, user, **kwargs):
    """Send a welcome email after successful registration."""

    message = f"""
        Hi,

        Welcome to our platform! We’re glad to have you onboard.

        Best regards,
        Your Team
    """
    # provider = SmsIrProvider()
    # provider.send_message(
    #     message=message, 
    #     phone_number=user.phone_number
    # )
    
    print(message)
