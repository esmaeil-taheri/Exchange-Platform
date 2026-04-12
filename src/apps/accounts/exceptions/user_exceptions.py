from apps.core.exceptions.base import DomainException


class OtpAlreadySent(DomainException):
    default_message = "Otp already Sent."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class FailedToSendOtp(DomainException):
    default_message = "Failed to send otp, Please try again later."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class InvalidOtp(DomainException):
    default_message = "Invalid Otp."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class TwoFactorAlreadyEnabled(DomainException):
    default_message = "2FA Already Enabled."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class TwoFactorAlreadyDisabled(DomainException):
    default_message = "2FA Already Disabled."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class InvalidTwoFactorCode(DomainException):
    default_message = "Invalid 2FA Code."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)