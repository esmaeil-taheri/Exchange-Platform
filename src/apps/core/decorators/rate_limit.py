"""
@rate_limit — decorator for DRF view methods

Usage:
    # Based only on IP
    @rate_limit(scope='otp_send_ip', limit=5, window=600)
    def post(self, request, ...): ...

    # Based on phone number (from request body)
    @rate_limit(scope='otp_send_phone', limit=3, window=600, key='phone', phone_field='phone_number')
    def post(self, request, ...): ...

    # Based on authenticated user (for authenticated endpoints)
    @rate_limit(scope='2fa_send', limit=3, window=600, key='user')
    def post(self, request, ...): ...

    # Combine multiple rules (all must pass)
    @rate_limit(scope='otp_send_phone', limit=3, window=600, key='phone')
    @rate_limit(scope='otp_send_ip',    limit=5, window=600, key='ip')
    def post(self, request, ...): ...

Headers added to the response:
    X-RateLimit-Limit     — total limit
    X-RateLimit-Remaining — remaining requests
    X-RateLimit-Reset     — seconds until reset

If blocked:
    HTTP 429 + Retry-After header
"""

import functools
import logging

from apps.core.utils.rate_limiter import limiter
from apps.core.utils.security_utils import get_client_ip
from apps.core.exceptions.rate_limit_exceptions import RateLimitExceeded

logger = logging.getLogger(__name__)


def rate_limit(
    scope: str,
    limit: int,
    window: int,
    key: str = 'ip',
    phone_field: str = 'phone_number',
):
    """
    Rate limit decorator for DRF APIView methods.

    Args:
        scope:        Unique name for this rule (e.g. 'otp_send_ip')
        limit:        Maximum allowed requests within the window
        window:       Time window (seconds)
        key:          Identifier type — 'ip' | 'user' | 'phone'
        phone_field:  Phone number field in request.data (when key='phone')
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(view_instance, request, *args, **kwargs):
            identifier = _resolve_identifier(request, key, phone_field)

            is_allowed, meta = limiter.check(
                scope=scope,
                identifier=identifier,
                limit=limit,
                window=window,
            )

            if not is_allowed:
                logger.warning(
                    f"[rate_limit] BLOCKED | scope={scope} key_type={key} "
                    f"identifier={_mask(identifier, key)} limit={limit} "
                    f"window={window}s retry_after={meta['retry_after']}s"
                )
                raise RateLimitExceeded(retry_after=meta['retry_after'])

            response = func(view_instance, request, *args, **kwargs)

            # ── Rate limit headers ────────────────────────────────────────
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Remaining'] = str(meta['remaining'])
            response['X-RateLimit-Reset'] = str(window)

            return response

        return wrapper
    return decorator


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_identifier(request, key: str, phone_field: str) -> str:
    if key == 'ip':
        return get_client_ip(request) or 'unknown'

    if key == 'user':
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.id}"
        return get_client_ip(request) or 'unknown'

    if key == 'phone':
        phone = (request.data or {}).get(phone_field, '').strip()
        return f"phone:{phone}" if phone else (get_client_ip(request) or 'unknown')

    return get_client_ip(request) or 'unknown'


def _mask(identifier: str, key: str) -> str:
    """Masks sensitive information for logging."""
    if key == 'phone' and identifier.startswith('phone:'):
        raw = identifier[6:]
        return f"phone:{raw[:4]}****{raw[-2:]}" if len(raw) > 6 else 'phone:***'
    if key == 'ip':
        parts = identifier.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.*.*"
    return identifier
