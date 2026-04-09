from apps.core.exceptions.base import DomainException

class RegistrationDisabled(DomainException):
    default_message = "User registration is currently disabled."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)

class UsernameAlreadyExists(DomainException):
    default_message = "User with this username already exists."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)