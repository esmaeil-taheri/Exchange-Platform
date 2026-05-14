from django.db import models
from django.db.models import Q


class Withdrawal(models.Model):

    class WithdrawalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT_TO_BANK = 'sent_to_bank', 'Sent To Bank'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        related_name='withdrawals',
        verbose_name='Customer'
    )

    card = models.ForeignKey(
        'customers.BankCard',
        on_delete=models.SET_NULL,
        null=True,
        related_name='withdrawals',
        verbose_name='Bank Card'
    )

    amount = models.BigIntegerField(
        default=0,
        verbose_name='Amount'
    )

    remaining_wallet_amount = models.BigIntegerField(
        default=0,
        verbose_name='Remaining Wallet Amount'
    )

    wallet_balance = models.BigIntegerField(
        default=0,
        verbose_name='Wallet Balance'
    )

    settlement_method = models.CharField(
        max_length=50,
        verbose_name='Settlement Method'
    )

    status = models.CharField(
        max_length=30,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING,
        db_index=True,
        verbose_name='Status'
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name='Is Verified'
    )

    bank_send = models.BooleanField(
        default=False,
        verbose_name='Sent To Bank'
    )

    is_instant = models.BooleanField(
        default=False,
        verbose_name='Is Instant'
    )

    inquiry_check = models.BooleanField(
        default=False,
        verbose_name='Inquiry Checked'
    )

    reject_reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Reject Reason'
    )

    desc = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Description'
    )

    wage = models.IntegerField(
        default=0,
        verbose_name='Wage'
    )

    vandar_amount = models.BigIntegerField(
        default=0,
        verbose_name='Vandar Amount'
    )

    vandar_status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Vandar Status'
    )

    track_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name='Track ID'
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        unique=True,
        null=True,
        db_index=True,
        verbose_name='Transaction ID'
    )

    iban = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='IBAN'
    )

    iban_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='IBAN ID'
    )

    settlement_date = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Settlement Date'
    )

    settlement_time = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Settlement Time'
    )

    process_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Processed At'
    )

    confirmed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Confirmed At'
    )

    errors = models.TextField(
        blank=True,
        null=True,
        verbose_name='Errors'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At'
    )

    class Meta:
        verbose_name = 'Withdrawal'
        verbose_name_plural = 'Withdrawals'

        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['customer']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['track_id']),
        ]

        constraints = [
            models.CheckConstraint(
                check=Q(amount__gte=0),
                name='withdrawal_amount_gte_0'
            ),
            models.CheckConstraint(
                check=Q(wage__gte=0),
                name='withdrawal_wage_gte_0'
            ),
            models.CheckConstraint(
                check=Q(wallet_balance__gte=0),
                name='wallet_balance_gte_0'
            ),
        ]

    def __str__(self):
        return f'Withdrawal #{self.pk} - {self.amount}'
