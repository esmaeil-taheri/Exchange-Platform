"""
Helpers for reading and canonicalising idempotency input.

The key comes from the `Idempotency-Key` request header. It is chosen by the
client and MUST identify the user's *intent*, not the attempt: every retry of
the same logical operation has to carry the same key, or the protection does
nothing.
"""

import hashlib
import json
import re
from decimal import Decimal

from django.conf import settings

from apps.core.exceptions.idempotency_exceptions import (
    IdempotencyKeyRequired,
    InvalidIdempotencyKey,
)

HEADER_NAME = 'Idempotency-Key'

# Deliberately narrow: a UUID4 hex, a ULID, or anything else opaque. Rejecting
# odd characters keeps the value safe to put in logs and cache keys.
_KEY_PATTERN = re.compile(r'^[A-Za-z0-9_\-:.]{8,64}$')


def extract_idempotency_key(request) -> str | None:
    """
    Read and validate the Idempotency-Key header.

    Returns None when the header is absent and settings.IDEMPOTENCY_REQUIRED
    is False, which leaves the endpoint behaving exactly as it did before.
    """
    raw = request.headers.get(HEADER_NAME) if hasattr(request, 'headers') else None

    if raw is not None:
        raw = raw.strip()

    if not raw:
        if getattr(settings, 'IDEMPOTENCY_REQUIRED', False):
            raise IdempotencyKeyRequired()
        return None

    if not _KEY_PATTERN.match(raw):
        raise InvalidIdempotencyKey()

    return raw


def build_request_fingerprint(params: dict) -> str:
    """
    sha256 over the canonicalised business parameters of a request.

    Canonical means: sorted keys, no whitespace, Decimals normalised through
    str(). Two requests that mean the same thing must produce the same digest,
    so this hashes the *validated* parameters rather than the raw body — JSON
    key order and formatting must not matter.
    """
    canonical = json.dumps(
        _normalise(params),
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _normalise(value):
    if isinstance(value, Decimal):
        # normalize() collapses 5.0 and 5.00 to the same representation, so a
        # retry that serialises the amount slightly differently still matches.
        return format(value.normalize(), 'f')
    if isinstance(value, dict):
        return {str(k): _normalise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, str)):
        return value
    return str(value)
