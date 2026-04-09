from typing import Optional

from rest_framework.exceptions import NotFound

from apps.accounts.models import CustomUser

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