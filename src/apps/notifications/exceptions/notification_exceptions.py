from apps.core.exceptions.base import DomainException


class NotificationAlreadyRead(DomainException):
    default_message = 'Notification already read.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
        

class NotificationNotFound(DomainException):
    default_message = 'Notification not found.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
        