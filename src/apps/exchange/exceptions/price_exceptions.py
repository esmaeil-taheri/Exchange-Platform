from apps.core.exceptions.base import DomainException


class InsufficientBuyAmount(DomainException):
    default_message = 'Amount is less than minimum buy amount'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class InsufficientSellAmount(DomainException):
    default_message = 'Amount is less than minimum sell amount'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)