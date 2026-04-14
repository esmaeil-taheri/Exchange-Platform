from rest_framework.permissions import BasePermission
from apps.customers.models.customer import Customer

class CanUploadKycDocument(BasePermission):
    message = "برای آپلود کارت ملی باید ابتدا مرحله اول احراز هویت را انجام دهید."

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        customer = getattr(user, "customer_profile", None)
        if customer is None:
            return False

        kyc = getattr(customer, "kyc", None)
        if kyc is None:
            return False

        return kyc.government_verified is True


class IsCustomerAuthenticated(BasePermission):
    message = "وضعیت حساب شما احراز هویت نشده است."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        customer = getattr(user, "customer_profile", None)
        if customer is None:
            return False

        return customer.status == Customer.CUSTOMERSTATUS[2][0]