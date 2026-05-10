from rest_framework.permissions import BasePermission
from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc


class CanUploadKycDocument(BasePermission):
    message = "برای آپلود مدرک هویتی ابتدا باید اطلاعات هویتی را تکمیل کنید"

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
        
        if kyc.status == Kyc.Status.PENDING_REVIEW:
            self.message = "مدرک هویتی شما در انتظار بررسی است"
            return False

        if kyc.status == Kyc.Status.APPROVED:
            self.message = "مدرک هویتی با با موفقیت تایید شده"
            return False
        
        return kyc.status == Kyc.Status.PENDING_UPLOAD or kyc.status == Kyc.Status.REJECTED


class IsCustomerAuthenticated(BasePermission):
    message = "برای استفاده از خدمات ابتدا باید احراز هویت کنید"

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        customer = getattr(user, "customer_profile", None)
        if customer is None:
            return False
        
        if customer.status == Customer.CUSTOMERSTATUS[1][0]:  # suspended
            self.message = "حساب کاربری شما مسدود شده است"
            return False

        return customer.status == Customer.CUSTOMERSTATUS[2][0]