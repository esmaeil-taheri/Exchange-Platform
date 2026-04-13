from django.urls import path

from apps.customers.api.views.customer_views import CustomerIdentityInquiryApiView, GetCustomerKycStatus

urlpatterns = [
    path('kyc/status/', GetCustomerKycStatus.as_view(), name='kyc-status'),
    path('kyc/verify-identity/', CustomerIdentityInquiryApiView.as_view(), name='verify-identity')
]
