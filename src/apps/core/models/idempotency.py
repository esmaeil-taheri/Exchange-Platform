from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    """
    One row per (user, endpoint, idempotency key).

    The unique constraint on that triple is the whole mechanism: the race
    between two simultaneous requests carrying the same key is resolved by
    PostgreSQL's unique index, not by an application-level `if exists()`.
    The loser of the insert blocks on the index until the winner commits or
    rolls back, then either replays the stored response or takes the key for
    itself. No window exists between the check and the insert, because there
    is no check.

    Two lifecycles share this table:

    `IN_PROGRESS` is only ever committed by endpoints that must leave their
    transaction to call an external gateway (buy-via-gateway, deposit).
    Everything else claims the key and finishes the work in a single
    transaction, so for those endpoints a committed row is always COMPLETED —
    an interrupted attempt rolls the row back along with the financial work it
    was guarding, which correctly frees the key for a genuine retry.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    class Endpoint(models.TextChoices):
        BUY = 'buy', 'Buy'
        SELL = 'sell', 'Sell'
        DEPOSIT = 'deposit', 'Deposit'
        WITHDRAW = 'withdraw', 'Withdraw'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='idempotency_records',
        verbose_name='User',
    )

    endpoint = models.CharField(
        max_length=32,
        choices=Endpoint.choices,
        verbose_name='Endpoint',
    )

    key = models.CharField(max_length=64, verbose_name='Idempotency Key')

    # sha256 of the canonicalised business parameters. Guards against a client
    # reusing one key for a different request — that is a client bug, and
    # replaying the first response would hide it.
    request_fingerprint = models.CharField(
        max_length=64, verbose_name='Request Fingerprint')

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name='Status',
    )

    response_body = models.JSONField(
        null=True, blank=True, verbose_name='Stored Response')

    # What this key produced, for audit: 'invoice:41', 'transaction:12',
    # 'withdrawal:7'. Lets a stuck key be resolved by a human without guessing.
    reference = models.CharField(
        max_length=64, blank=True, verbose_name='Reference')

    correlation_id = models.CharField(
        max_length=64, blank=True, verbose_name='Correlation ID')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Idempotency Record'
        verbose_name_plural = 'Idempotency Records'
        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'endpoint', 'key'],
                name='uniq_idempotency_user_endpoint_key',
            ),
        ]

        indexes = [
            models.Index(fields=['created_at'], name='idem_created_at_idx'),
            models.Index(fields=['status', 'created_at'], name='idem_status_created_idx'),
        ]

    def __str__(self):
        return f'{self.endpoint}:{self.key} ({self.status})'
