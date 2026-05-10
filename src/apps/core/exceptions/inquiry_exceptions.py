from apps.core.exceptions.base import DomainException, InfrastrctureException


class InquiryServiceError(InfrastrctureException):
    default_message = "Inquiry Service Error."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class KycInquiryFailed(DomainException):
    default_message = "Inquiry Failed."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
