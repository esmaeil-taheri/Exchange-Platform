from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.exceptions.user_exceptions import (
    InvalidTwoFactorCode,
    OtpAlreadySent,
    FailedToSendOtp,
    InvalidOtp,
    TwoFactorAlreadyDisabled,
    TwoFactorAlreadyEnabled
)

from apps.core.exceptions.base import ActionDisabled
from apps.notifications.exceptions.notification_exceptions import (
    NotificationAlreadyRead, NotificationNotFound
)
from apps.customers.exceptions.customer_exceptions import CustomerAlreadyVerified


def custom_exception_handler(exc, context):

    if isinstance(exc, ActionDisabled):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, OtpAlreadySent):
        return _error_response(exc, status.HTTP_429_TOO_MANY_REQUESTS)

    if isinstance(exc, InvalidOtp):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, TwoFactorAlreadyEnabled):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, TwoFactorAlreadyDisabled):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, InvalidTwoFactorCode):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, NotificationAlreadyRead):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, CustomerAlreadyVerified):
        return _error_response(exc, status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, NotificationNotFound):
        return _error_response(exc, status.HTTP_404_NOT_FOUND)

    if isinstance(exc, FailedToSendOtp):
        return _error_response(exc, status.HTTP_503_SERVICE_UNAVAILABLE)

    return exception_handler(exc, context)


def _error_response(exc, status_code):
    return Response(
        {
            "message": str(exc),
        },
        status=status_code,
    )
