from typing import Optional

from rest_framework.exceptions import NotFound

from apps.accounts.models import CustomUser
from apps.core.utils.security_utils import get_totp_uri

class UserSelector:
    """Encapsulate all 'read' operations related to User."""

    @staticmethod
    def get_user_by_email(email: str) -> Optional[CustomUser]:
        return CustomUser.objects.filter(email=email).first()

    @staticmethod
    def get_user_by_id(user_id: int) -> CustomUser:
        user = CustomUser.objects.get(id=user_id)
        if not user:
            raise NotFound("User not found")
        return user
    
    @staticmethod
    def get_user_2fa_uri(user_id: int) -> dict:

        user = CustomUser.objects.filter(id=user_id).only(
            "totp_secret", "national_id").first()

        uri = get_totp_uri(
            secret=user.totp_secret,
            identifier=user.national_id
        )

        return {
            "setup_key": user.totp_secret,
            "uri": uri
        }