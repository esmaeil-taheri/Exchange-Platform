from django.urls import path

from apps.accounts.api.views.user_views import (
    Change2FAStatusApiView, LoginRegisterApiView, LoginRegisterVerifyApiView, 
    Verify2FAAccessApiView, Get2FAUriApiView
)

urlpatterns = [
    path("login-register/", LoginRegisterApiView.as_view(), name="login-register"),
    path('verify/', LoginRegisterVerifyApiView.as_view(), name='login-register-verify'),
    path('2fa/', Get2FAUriApiView.as_view(), name='2fa-uri'),
    path('2fa/verify/', Verify2FAAccessApiView.as_view(), name='send-2fa-code'),
    path('2fa/change/', Change2FAStatusApiView.as_view(), name='change-2fa-status')
]
