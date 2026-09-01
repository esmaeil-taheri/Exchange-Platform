"""
Idempotency for financial endpoints.

The guarantee this provides:

    same request + same idempotency key  ==  exactly one financial effect

Two shapes are supported, and the difference matters:

1. `acquire(...)` — for operations whose entire financial effect happens in one
   database transaction (sell, buy-from-wallet, withdrawal request). The caller
   opens `transaction.atomic()`, acquires the guard, does the work, calls
   `complete()`, and lets the block commit. Claim and effect commit together,
   so there is no window in which one exists without the other. If the work
   raises, the guard row rolls back with it and the key is free again — which
   is what a failed request should do.

2. `acquire(..., external=True)` — for operations that must leave the
   transaction to call a payment gateway (buy-via-gateway, deposit). The claim
   commits first as IN_PROGRESS, the external call runs unlocked, then
   `complete()` records the response. A crash in between leaves an IN_PROGRESS
   row; `release()` on the error path frees it immediately, and a stale row is
   reclaimable after IDEMPOTENCY_IN_PROGRESS_TIMEOUT_SECONDS. The effect being
   guarded there is an unpaid invoice, so reclaiming is cheap — the worst case
   is a second unpaid invoice, which is exactly today's behaviour.

Never call `acquire()` outside a transaction for shape 1: the whole point is
that the INSERT and the financial write share a commit.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions.idempotency_exceptions import (
    IdempotencyKeyConflict,
    IdempotentRequestInProgress,
)
from apps.core.middlewares.request_id_middleware import get_request_id
from apps.core.models.idempotency import IdempotencyRecord
from apps.core.utils.idempotency_utils import build_request_fingerprint
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


DEFAULT_IN_PROGRESS_TIMEOUT_SECONDS = 120


@dataclass
class IdempotencyGuard:
    """A claimed key. Call complete() once the guarded work has been done."""

    record: IdempotencyRecord
    replayed: bool = False
    response: dict | None = None
    _external: bool = field(default=False, repr=False)

    def complete(self, response: dict, reference: str = '') -> None:
        """
        Mark the key as spent and store the response for future replays.

        For an in-transaction guard this is a plain UPDATE inside the caller's
        atomic block. For an external guard it opens its own short transaction,
        because the caller's has already committed.
        """
        self.record.status = IdempotencyRecord.Status.COMPLETED
        self.record.response_body = response
        if reference:
            self.record.reference = reference

        fields = ['status', 'response_body', 'reference', 'updated_at']

        if self._external:
            with transaction.atomic():
                self.record.save(update_fields=fields)
        else:
            self.record.save(update_fields=fields)

    def set_reference(self, reference: str) -> None:
        """Record what this key produced before the work is finished."""
        self.record.reference = reference
        self.record.save(update_fields=['reference', 'updated_at'])

    def release(self) -> None:
        """
        Give the key back after a failure on an external-call path.

        Only meaningful for `external=True` guards — an in-transaction guard is
        released by the rollback of the caller's atomic block.
        """
        if not self._external:
            return
        IdempotencyRecord.objects.filter(
            id=self.record.id,
            status=IdempotencyRecord.Status.IN_PROGRESS,
        ).delete()


class NullGuard:
    """
    Stand-in used when a request carries no key.

    Keeps every call site free of `if key:` branches, so the guarded and
    unguarded paths cannot drift apart.
    """

    replayed = False
    response = None
    record = None

    def complete(self, response: dict, reference: str = '') -> None:
        return None

    def set_reference(self, reference: str) -> None:
        return None

    def release(self) -> None:
        return None


class IdempotencyService:

    @staticmethod
    def acquire(
        *,
        user_id: int,
        endpoint: str,
        key: str | None,
        params: dict,
        external: bool = False,
    ):
        """
        Claim an idempotency key, or surface what the previous holder did.

        Returns a guard whose `replayed` flag tells the caller whether to do
        the work or to return `guard.response` verbatim.

        Raises:
            IdempotencyKeyConflict:       key reused for a different request
            IdempotentRequestInProgress:  an external-call attempt is still running
        """
        if not key:
            return NullGuard()

        fingerprint = build_request_fingerprint(params)

        try:
            # Nested atomic == savepoint. Without it, the IntegrityError below
            # would poison the caller's outer transaction and every later
            # statement in it would fail with "current transaction is aborted".
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    user_id=user_id,
                    endpoint=endpoint,
                    key=key,
                    request_fingerprint=fingerprint,
                    status=IdempotencyRecord.Status.IN_PROGRESS,
                    correlation_id=get_request_id(),
                )
        except IntegrityError:
            return IdempotencyService._resolve_existing(
                user_id=user_id,
                endpoint=endpoint,
                key=key,
                fingerprint=fingerprint,
                external=external,
            )

        logger.info(
            f"[idempotency] Key claimed | endpoint={endpoint} key={key} "
            f"user_id={user_id} external={external}"
        )
        return IdempotencyGuard(record=record, replayed=False, _external=external)

    @staticmethod
    def _resolve_existing(*, user_id, endpoint, key, fingerprint, external):
        """
        The key was already taken. Decide between replay, conflict and retry.

        Reached only after the INSERT lost the race on the unique index, which
        means the winner has already committed — so this read sees its final
        state, not a half-written one.
        """
        record = (
            IdempotencyRecord.objects
            .select_for_update()
            .get(user_id=user_id, endpoint=endpoint, key=key)
        )

        if record.request_fingerprint != fingerprint:
            logger.warning(
                f"[idempotency] Key REUSED for a different request | "
                f"endpoint={endpoint} key={key} user_id={user_id}"
            )
            raise IdempotencyKeyConflict()

        if record.status == IdempotencyRecord.Status.COMPLETED:
            logger.info(
                f"[idempotency] Replaying stored response | endpoint={endpoint} "
                f"key={key} user_id={user_id} reference={record.reference or '-'}"
            )
            return IdempotencyGuard(
                record=record,
                replayed=True,
                response=record.response_body,
                _external=external,
            )

        # Still IN_PROGRESS. For an in-transaction endpoint this state is never
        # committed, so seeing it here means an external-call attempt.
        if IdempotencyService._is_stale(record):
            logger.warning(
                f"[idempotency] Reclaiming stale in-progress key | endpoint={endpoint} "
                f"key={key} user_id={user_id} reference={record.reference or '-'}"
            )
            record.request_fingerprint = fingerprint
            record.correlation_id = get_request_id()
            record.created_at = timezone.now()
            record.save(update_fields=[
                'request_fingerprint', 'correlation_id', 'created_at', 'updated_at'])
            return IdempotencyGuard(record=record, replayed=False, _external=external)

        logger.info(
            f"[idempotency] Concurrent request rejected | endpoint={endpoint} "
            f"key={key} user_id={user_id}"
        )
        raise IdempotentRequestInProgress()

    @staticmethod
    def _is_stale(record: IdempotencyRecord) -> bool:
        timeout = getattr(
            settings,
            'IDEMPOTENCY_IN_PROGRESS_TIMEOUT_SECONDS',
            DEFAULT_IN_PROGRESS_TIMEOUT_SECONDS,
        )
        return record.created_at < timezone.now() - timedelta(seconds=timeout)
