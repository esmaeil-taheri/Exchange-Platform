from apps.core.exceptions.base import DomainException


class RateLimitExceeded(DomainException):
    """
    rate limit exceeded.

    Attributes:
        retry_after: the seconds user has to wait
    """

    default_message = "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کنید."

    def __init__(self, message: str = None, retry_after: int = 0):
        self.retry_after = retry_after
        super().__init__(message or self.default_message)
