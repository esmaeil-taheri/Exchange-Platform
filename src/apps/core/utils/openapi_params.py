"""Reusable drf-spectacular parameters."""

from drf_spectacular.utils import OpenApiParameter

IDEMPOTENCY_KEY_PARAMETER = OpenApiParameter(
    name='Idempotency-Key',
    location=OpenApiParameter.HEADER,
    required=False,
    type=str,
    description=(
        'Client-generated key (8–64 chars of A-Z a-z 0-9 _ - : .) that makes '
        'this request safe to retry. Generate it once per user intent — a UUID4 '
        'when the customer taps the button — and send the SAME value on every '
        'retry of that operation, including after a timeout. Repeating a key '
        'returns the original response without repeating the financial effect. '
        'Reusing a key with a different body returns 422. If a previous attempt '
        'with this key is still running the response is 409 with Retry-After; '
        'retry the same key. A NEW operation must always use a NEW key.'
    ),
)
