from django.urls import path

from apps.customers.api.views.customer_views import (
    CustomerIdentityInquiryApiView, GetCustomerKycStatus, 
    CustomerKycUploadDocApiView
)

from apps.customers.api.views.card_views import (
    BankCardListApiView, 
    CreateBankCardApiView, 
    DeleteBankCardApiView
)

urlpatterns = [
    path('kyc/status/', GetCustomerKycStatus.as_view(), name='kyc-status'),
    path('kyc/verify-identity/', CustomerIdentityInquiryApiView.as_view(), name='verify-identity'),
    path('kyc/upload-doc/', CustomerKycUploadDocApiView.as_view(), name='kyc-upload-doc'),
    path('card/', BankCardListApiView.as_view(), name='get-bank-cards'),
    path('card/create', CreateBankCardApiView.as_view(), name='create-bank-card'),
    path('card/<int:card_id>', DeleteBankCardApiView.as_view(), name='delete-bank-card')
]
