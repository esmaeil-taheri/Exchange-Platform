from apps.core.exceptions.base import DomainException


class CurrencyNotFound(DomainException):
    default_message = 'Currency not found.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class CurrencyNotBuyable(DomainException):
    default_message = 'Currency buying is disabled.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)