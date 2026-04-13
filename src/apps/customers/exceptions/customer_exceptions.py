from apps.core.exceptions.base import DomainException


class CustomerAlreadyVerified(DomainException):
    default_message = "Customer already verified"

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class CustomerAlreadyUploadedDoc(DomainException):
    default_message = "Otp already upload the document."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
