class DomainException(Exception):
    pass


class InfrastrctureException(Exception):
    pass


class ActionDisabled(DomainException):
    default_message = "This action is currently disabled."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)