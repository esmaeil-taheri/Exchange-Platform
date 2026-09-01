from apps.core.exceptions.base import DomainException


class IdempotencyKeyRequired(DomainException):
    """No Idempotency-Key header on an endpoint that requires one."""

    default_message = (
        'ارسال هدر Idempotency-Key برای این درخواست الزامی است.'
    )

    def __init__(self, message: str = None):
        super().__init__(message or self.default_message)


class InvalidIdempotencyKey(DomainException):
    """The header was present but malformed."""

    default_message = (
        'مقدار Idempotency-Key نامعتبر است. حداکثر ۶۴ کاراکتر از حروف، ارقام، '
        'خط تیره و زیرخط مجاز است.'
    )

    def __init__(self, message: str = None):
        super().__init__(message or self.default_message)


class IdempotencyKeyConflict(DomainException):
    """
    Same key, different request body.

    Never replay in this case: the client reused a key for a different
    operation, which is a client bug. Replaying the first response would
    silently swallow the second, genuinely different, request.
    """

    default_message = (
        'این Idempotency-Key قبلاً برای درخواست دیگری استفاده شده است.'
    )

    def __init__(self, message: str = None):
        super().__init__(message or self.default_message)


class IdempotentRequestInProgress(DomainException):
    """
    Another request with this key is still running.

    The client should retry after a short delay — the first attempt will
    either complete (and the retry replays its response) or fail (and the
    retry takes the key).
    """

    default_message = (
        'درخواست قبلی با همین شناسه هنوز در حال پردازش است. '
        'لطفاً چند لحظه بعد مجدداً تلاش کنید.'
    )

    def __init__(self, message: str = None, retry_after: int = 3):
        self.retry_after = retry_after
        super().__init__(message or self.default_message)
