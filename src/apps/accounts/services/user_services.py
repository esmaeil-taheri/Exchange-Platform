from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.dispatch import Signal

from apps.accounts.models import CustomUser
from apps.site_setting.selectors.setting_selectors import get_site_settings
from apps.accounts.exceptions.user_exceptions import RegistrationDisabled, UsernameAlreadyExists

# define a signal
user_registered = Signal()  # args: user


class UserService:

    @staticmethod
    @transaction.atomic
    def register_user(*, username: str, email: str, password: str) -> CustomUser:
        settings = get_site_settings()

        if not settings.customer_register:
            raise RegistrationDisabled(message="User registration is currently disabled.")
        
        if CustomUser.objects.filter(username=username).exists():
            raise UsernameAlreadyExists("User with this username already exists.")

        user = CustomUser(
            username=username,
            email=email,
            password=make_password(password),
        )
        user.save()

        # fire signal
        user_registered.send(sender=CustomUser, user=user)

        return user
