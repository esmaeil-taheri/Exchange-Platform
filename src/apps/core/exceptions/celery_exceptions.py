from apps.core.exceptions.base import InfrastrctureException


class CeleryDispatchError(InfrastrctureException):
    default_message = "Celery dispatch error."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)