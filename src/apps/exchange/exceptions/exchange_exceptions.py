from apps.core.exceptions.base import DomainException


class InsufficientSystemBalance(DomainException):
    default_message = 'Amount is more than system balance'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class InsufficientUserBalance(DomainException):
    default_message = 'Amount is more than user balance'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
