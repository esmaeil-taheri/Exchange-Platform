from apps.core.exceptions.base import DomainException


class DailyLimitExceeded(DomainException):
    default_message = 'Daily limit exceeded.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)