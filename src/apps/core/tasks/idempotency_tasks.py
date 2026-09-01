from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.core.models.idempotency import IdempotencyRecord
from apps.core.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_RETENTION_HOURS = 48
CLEANUP_BATCH_SIZE = 5000


@shared_task()
def purge_expired_idempotency_records():
    """
    Drop idempotency records past their replay window.

    Retention is a product decision, not a safety one: once a client has
    stopped retrying, the row only costs storage. Keep it long enough to cover
    every realistic retry (mobile clients resuming after hours offline), then
    let it go.

    Deleting in bounded batches so a backlog cannot turn into one enormous
    DELETE holding locks across the table.
    """
    retention_hours = getattr(
        settings, 'IDEMPOTENCY_RETENTION_HOURS', DEFAULT_RETENTION_HOURS)
    cutoff = timezone.now() - timedelta(hours=retention_hours)

    ids = list(
        IdempotencyRecord.objects
        .filter(created_at__lt=cutoff)
        .values_list('id', flat=True)[:CLEANUP_BATCH_SIZE]
    )

    if not ids:
        return 0

    deleted, _ = IdempotencyRecord.objects.filter(id__in=ids).delete()

    logger.info(
        f"[task=purge_idempotency] Removed {deleted} expired record(s) "
        f"older than {retention_hours}h"
    )
    return deleted


@shared_task()
def report_stuck_idempotency_records():
    """
    Surface keys stuck IN_PROGRESS far beyond any plausible request.

    Only the external-gateway paths can commit an IN_PROGRESS row, and only
    when the process died between claiming the key and recording the response.
    Each one is a request whose outcome the client was never told, so it is
    worth an alert rather than silent cleanup.
    """
    cutoff = timezone.now() - timedelta(minutes=30)

    stuck = list(
        IdempotencyRecord.objects
        .filter(status=IdempotencyRecord.Status.IN_PROGRESS, created_at__lt=cutoff)
        .order_by('created_at')[:100]
    )

    if not stuck:
        return 0

    logger.error(
        f"[task=stuck_idempotency] {len(stuck)} idempotency key(s) stuck in progress — "
        f"each is a request whose outcome was never returned to the client"
    )
    for record in stuck:
        logger.error(
            f"[task=stuck_idempotency] endpoint={record.endpoint} key={record.key} "
            f"user_id={record.user_id} reference={record.reference or '-'} "
            f"correlation_id={record.correlation_id or '-'} created_at={record.created_at}"
        )

    return len(stuck)
