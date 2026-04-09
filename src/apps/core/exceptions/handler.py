from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.exceptions.user_exceptions import (
    RegistrationDisabled,
    UsernameAlreadyExists,
)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, RegistrationDisabled):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    if isinstance(exc, UsernameAlreadyExists):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT
        )

    return response