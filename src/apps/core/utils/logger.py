import logging
from apps.core.middlewares.request_id_middleware import get_request_id, get_user_id


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request_id and user_id to every log record.
    It must be added to each handler or logger.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Returns the project's standard logger.
    request_id and user_id are automatically added to every log.

    Usage:
        from apps.core.utils.logger import get_logger
        logger = get_logger(__name__)

        logger.info("Purchase started | asset=XAU18 amount=500000")
        logger.warning("Insufficient balance | user_id=42 balance=1000")
        logger.error("Error communicating with gateway | invoice_id=99")
    """
    logger = logging.getLogger(name)

    # Add filter if it hasn't been added already
    if not any(isinstance(f, RequestContextFilter) for f in logger.filters):
        logger.addFilter(RequestContextFilter())

    return logger
