from apps.core.exceptions.base import DomainException


class CustomerAlreadyVerified(DomainException):
    default_message = "Otp already Sent."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
