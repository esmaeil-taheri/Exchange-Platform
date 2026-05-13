from django.urls import path

from apps.payments.api.views.payments_views import DepositApiView, ZarinpalCallbackApiView


urlpatterns = [
    path('zarinpal/callback', ZarinpalCallbackApiView.as_view(), name='zarinpal-payment-callback'),
    path('deposit', DepositApiView.as_view(), name='deposit-funds'),
]
