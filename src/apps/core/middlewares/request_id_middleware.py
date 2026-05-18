import uuid
import threading

# Thread-local storage — each request has its own separate space
_request_context = threading.local()


def get_request_id() -> str:
    """Returns the current Request ID. If not in context, returns '-'."""
    return getattr(_request_context, 'request_id', '-')


def get_user_id() -> str:
    """Returns the current User ID. If not authenticated, returns 'anon'."""
    return getattr(_request_context, 'user_id', 'anon')


def set_request_context(request_id: str, user_id: str = 'anon') -> None:
    _request_context.request_id = request_id
    _request_context.user_id = user_id


def clear_request_context() -> None:
    _request_context.request_id = '-'
    _request_context.user_id = 'anon'


class RequestIdMiddleware:
    """
    Middleware that generates a short UUID (8 characters) for each HTTP request.

    - Stores request_id and user_id in thread-local storage
    - Adds X-Request-Id to the response headers
    - Clears the context after the request is finished

    Usage in logger:
        from apps.core.middlewares.request_id_middleware import get_request_id
        logger.info(f"message | request_id={get_request_id()}")
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If X-Request-Id is provided by an upstream (like nginx), use that
        request_id = request.headers.get('X-Request-Id') or uuid.uuid4().hex[:8]

        # Read user_id from JWT or session
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'anon'

        set_request_context(request_id=request_id, user_id=user_id)

        # Also attach request_id to the request object (for use in views)
        request.request_id = request_id

        response = self.get_response(request)

        # Add request_id to response headers for client-side tracing
        response['X-Request-Id'] = request_id

        clear_request_context()

        return response
