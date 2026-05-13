from apps.core.exceptions.base import DomainException


class InvoiceNotFound(DomainException):
    default_message = "Invoice not found."

    def __init__(self, message=None):
        super().__init__(message or self.message)
