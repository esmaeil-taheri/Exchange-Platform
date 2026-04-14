from apps.core.exceptions.base import DomainException


class BankCardAlreadyExists(DomainException):
    default_message = "BankCard already exists."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class BankCardNotFound(DomainException):
    default_message = 'BankCard not found.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
