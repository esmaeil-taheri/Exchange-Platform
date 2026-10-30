from rest_framework.permissions import IsAuthenticated


class IsTwoFactorAuthenticated(IsAuthenticated):
    message = "Two-factor authentication is required."
    code = "two_factor_required"

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return not request.user.is_2fa_enabled or not request.user.requires_2fa
