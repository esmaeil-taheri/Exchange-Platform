from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings

from apps.settlements.models.withdrawal import Withdrawal
from apps.core.services.settlement.vandar import VandarClient
from apps.exchange.models.wallet import Wallet
from apps.core.utils.date_time_utils import get_date_time

import logging


logger = logging.getLogger(__name__)


# How long a withdrawal may sit un-dispatched before the safety net requeues it.
# Low stakes: process_withdrawal_requests is idempotent, so a needless requeue
# costs nothing.
STUCK_WITHDRAWAL_AGE_MINUTES = 5
STUCK_WITHDRAWAL_BATCH_SIZE = 20

# How long we wait before treating a PSP "track_id not found" as proof the payout
# never reached the bank, and refunding the customer.
#
# Deliberately NOT the 5 minutes above. Refunding here is irreversible in
# practice: if the settlement was actually in flight and merely not yet visible
# to the inquiry API, the customer is paid twice. Paya settles in batches, so a
# freshly submitted payout can legitimately be unqueryable for a long while.
# The cost of waiting is a delayed refund; the cost of being early is a double
# payout. Wait.
UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES = 180

# Rows examined per inquiry run.
INQUIRY_BATCH_SIZE = 5


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 5},
)
def process_withdrawal_requests(self, withdrawal_id):

    token = settings.VANDAR_API_KEY
    business = settings.VANDAR_BUSINESS_NAME

    vandar = VandarClient(token=token, business=business)

    try:
        # ── Step 1: Claim Phase (Atomic & Lock-Safe) ───────────────────────────
        # Lock the row with select_for_update(skip_locked=True) and transition
        # status to PROCESSING inside a short transaction. This prevents any
        # concurrent worker from claiming or double-sending this withdrawal.
        with transaction.atomic():
            withdrawal = (
                Withdrawal.objects
                .select_for_update(of=('self',), skip_locked=True)
                .select_related('customer__user', 'card')
                .filter(id=withdrawal_id, status=Withdrawal.WithdrawalStatus.PENDING)
                .first()
            )

            if withdrawal is None:
                logger.info(
                    f"[task=process_withdrawal] Withdrawal {withdrawal_id} skipped — "
                    f"already claimed or not in PENDING status"
                )
                return f"Withdrawal {withdrawal_id} already processed or currently claimed"

            if withdrawal.track_id:
                logger.info(
                    f"[task=process_withdrawal] Withdrawal {withdrawal_id} skipped — "
                    f"already has track_id: {withdrawal.track_id}"
                )
                return f"Withdrawal {withdrawal_id} already has track_id"

            track_id = str(withdrawal.id)
            customer = withdrawal.customer
            card = withdrawal.card

            iban = card.Shaba_number
            national_code = customer.user.national_id
            birth_date = customer.birth_date
            amount_to_settle = withdrawal.amount - vandar.wage

            withdrawal.status = Withdrawal.WithdrawalStatus.PROCESSING
            withdrawal.track_id = track_id
            withdrawal.save(update_fields=['status', 'track_id'])

        # ── Step 2: External HTTP Call (Outside DB Lock) ──────────────────────
        # DB connection is released before making the network request to Vandar.
        response = vandar.create_settlement(
            amount=amount_to_settle,
            iban=iban,
            track_id=track_id,
            payment_number=str(withdrawal.id),
            description=f"withdrawal #{withdrawal.id}",
            national_code=national_code,
            birth_date=birth_date,
        )

        # ── Step 3: Finalize / Settle Phase (Atomic) ──────────────────────────
        with transaction.atomic():
            withdrawal = Withdrawal.objects.select_for_update().get(id=withdrawal_id)

            if response.get("error"):
                error_message = response.get("message", "Unknown PSP error")
                is_definitive_failure = response.get("is_definitive_failure", False)
                now_ts = get_date_time()['timestamp']

                if is_definitive_failure:
                    # Definitive business rejection by PSP (e.g. invalid IBAN, account mismatch)
                    # Safe to mark FAILED and refund immediately
                    withdrawal.status = Withdrawal.WithdrawalStatus.FAILED
                    withdrawal.errors = error_message
                    withdrawal.save(update_fields=["status", "errors"])

                    Wallet.objects.create(
                        customer=withdrawal.customer,
                        wallet_type='irt',
                        amount=withdrawal.amount,
                        desc=f'برگشت وجه بابت رد درخواست تسویه #{withdrawal.id} توسط درگاه',
                        ip='0.0.0.0',
                        created_at=now_ts,
                        verified_at=now_ts,
                        is_verified=True,
                    )

                    logger.warning(
                        f"[task=process_withdrawal] Settlement rejected definitively by PSP — IRT refunded | "
                        f"withdrawal_id={withdrawal_id} customer_id={withdrawal.customer_id} "
                        f"amount={withdrawal.amount}IRT reason={error_message}"
                    )

                    return f"PSP Definitive Error: {error_message}"

                else:
                    # Network timeout / Connection error / 5xx (Unconfirmed state) — DO NOT REFUND!
                    # Mark as SENT_TO_BANK with track_id so inquiry_processed_withdrawals can safely verify status.
                    withdrawal.status = Withdrawal.WithdrawalStatus.SENT_TO_BANK
                    withdrawal.bank_send = True
                    withdrawal.errors = f"Unconfirmed PSP state: {error_message}"
                    withdrawal.process_time = timezone.now()
                    withdrawal.save(update_fields=[
                        "status", "bank_send", "errors", "process_time"
                    ])

                    logger.warning(
                        f"[task=process_withdrawal] Settlement network/timeout error — "
                        f"marked SENT_TO_BANK for inquiry (no refund) | "
                        f"withdrawal_id={withdrawal_id} track_id={track_id} error={error_message}"
                    )

                    return f"PSP Unconfirmed (marked for inquiry): {error_message}"

            settlement_data = response.get("data", {}).get("settlement", [])
            settlement = settlement_data[0] if isinstance(settlement_data, list) and settlement_data else (settlement_data if isinstance(settlement_data, dict) else {})

            raw_tx_id = settlement.get("transaction_id")
            withdrawal.transaction_id = str(raw_tx_id) if raw_tx_id else None
            withdrawal.vandar_amount = settlement.get("amount", withdrawal.amount)
            withdrawal.wage = settlement.get("wage_toman", 0)
            withdrawal.vandar_status = settlement.get("status", "")
            withdrawal.iban = settlement.get("iban", iban)
            withdrawal.desc = settlement.get("description", "")
            withdrawal.settlement_date = settlement.get("settlement_date", "")
            withdrawal.settlement_time = settlement.get("settlement_time", "")
            withdrawal.is_instant = settlement.get("is_instant", True)

            withdrawal.status = Withdrawal.WithdrawalStatus.SENT_TO_BANK
            withdrawal.bank_send = True
            withdrawal.process_time = timezone.now()

            withdrawal.save()

        return f"Withdrawal {withdrawal_id} successfully sent to bank"

    except Withdrawal.DoesNotExist:
        error_msg = f"Withdrawal {withdrawal_id} not found"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        logger.exception(
            f"Unexpected error in process_withdrawal_requests for: {withdrawal_id}"
        )
        raise e 


@shared_task()
def inquiry_processed_withdrawals():

    token = settings.VANDAR_API_KEY
    business = settings.VANDAR_BUSINESS_NAME

    # Least-recently-inquired first (never-inquired rows lead). Ordering by
    # created_at instead would let a row the PSP keeps erroring on sit at the head
    # of the window forever, starving every newer withdrawal of its inquiry.
    pendings = Withdrawal.objects.filter(
        status__in=[Withdrawal.WithdrawalStatus.SENT_TO_BANK, Withdrawal.WithdrawalStatus.PROCESSING]
    ).exclude(track_id='').order_by(
        F('last_inquiry_at').asc(nulls_first=True), 'created_at'
    )[:INQUIRY_BATCH_SIZE]

    if not pendings:
        return

    vandar = VandarClient(token=token, business=business)

    for pending in pendings:

        try:

            withdrawal = Withdrawal.objects.get(id=pending.id)

            if withdrawal.status not in [Withdrawal.WithdrawalStatus.SENT_TO_BANK, Withdrawal.WithdrawalStatus.PROCESSING]:
                continue

            # Stamp before the call: an attempt that raises must still rotate this
            # row to the back, otherwise it would be retried on every single run.
            Withdrawal.objects.filter(id=withdrawal.id).update(last_inquiry_at=timezone.now())

            response = vandar.inquiry_settlement(withdrawal.track_id)

            if response.get("error"):
                error_msg = response.get("message")
                is_not_found = response.get("is_not_found", False)
                age_minutes = (timezone.now() - withdrawal.created_at).total_seconds() / 60

                # If PSP definitively confirms track_id was not found (404) AND the withdrawal
                # is older than the safety threshold, the worker had crashed before Vandar received
                # the payout. We safely fail the withdrawal and refund the wallet.
                if is_not_found and age_minutes >= UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES:
                    with transaction.atomic():
                        withdrawal = Withdrawal.objects.select_for_update().get(id=pending.id)
                        if withdrawal.status not in [Withdrawal.WithdrawalStatus.SENT_TO_BANK, Withdrawal.WithdrawalStatus.PROCESSING]:
                            continue

                        withdrawal.status = Withdrawal.WithdrawalStatus.FAILED
                        withdrawal.is_verified = False
                        withdrawal.errors = "PSP track_id not found — request never reached gateway"
                        withdrawal.save(update_fields=["status", "is_verified", "errors"])

                        now_ts = get_date_time()['timestamp']
                        Wallet.objects.create(
                            customer=withdrawal.customer,
                            wallet_type='irt',
                            amount=withdrawal.amount,
                            desc=f'برگشت وجه بابت عدم ثبت درخواست تسویه در درگاه — درخواست برداشت #{withdrawal.id}',
                            ip='0.0.0.0',
                            created_at=now_ts,
                            verified_at=now_ts,
                            is_verified=True,
                        )

                        logger.warning(
                            f"[task=inquiry_withdrawal] Stale withdrawal not found in PSP — FAILED and refunded | "
                            f"withdrawal_id={withdrawal.id} customer_id={withdrawal.customer_id} "
                            f"amount={withdrawal.amount}IRT"
                        )
                else:
                    withdrawal.errors = error_msg
                    withdrawal.save(update_fields=["errors"])

                continue

            settlement = response["data"]["settlements"][0]
            status = settlement.get("status")

            with transaction.atomic():

                withdrawal = Withdrawal.objects.select_for_update().get(id=pending.id)

                # Re-check status under row lock to prevent race conditions across parallel inquiry tasks
                if withdrawal.status not in [Withdrawal.WithdrawalStatus.SENT_TO_BANK, Withdrawal.WithdrawalStatus.PROCESSING]:
                    continue

                withdrawal.vandar_status = status
                withdrawal.inquiry_check = True

                if status == "DONE":
                    withdrawal.status = Withdrawal.WithdrawalStatus.COMPLETED
                    withdrawal.is_verified = True
                    withdrawal.confirmed_at = timezone.now()
                    logger.info(
                        f"[task=inquiry_withdrawal] Settlement COMPLETED | "
                        f"withdrawal_id={withdrawal.id} customer_id={withdrawal.customer_id} "
                        f"amount={withdrawal.amount}IRT"
                    )

                elif status in ["FAILED", "CANCELED"]:
                    withdrawal.status = Withdrawal.WithdrawalStatus.FAILED
                    withdrawal.is_verified = False
                    withdrawal.reject_reason = status

                    now_ts = get_date_time()['timestamp']
                    Wallet.objects.create(
                        customer=withdrawal.customer,
                        wallet_type='irt',
                        amount=withdrawal.amount,
                        desc=f'برگشت وجه بابت رد شدن تسویه — درخواست برداشت #{withdrawal.id}',
                        ip='0.0.0.0',
                        created_at=now_ts,
                        verified_at=now_ts,
                        is_verified=True,
                    )
                    logger.warning(
                        f"[task=inquiry_withdrawal] Settlement {status} — IRT refunded | "
                        f"withdrawal_id={withdrawal.id} customer_id={withdrawal.customer_id} "
                        f"amount={withdrawal.amount}IRT"
                    )

                withdrawal.save(
                    update_fields=[
                        "status",
                        "vandar_status",
                        "is_verified",
                        "reject_reason",
                        "confirmed_at",
                        "inquiry_check",
                    ]
                )

        except Exception as e:
            logger.exception(
                f"Unexpected error in process_withdrawal_requests for: {pending.id}"
            )
            continue


@shared_task()
def process_stuck_withdrawals():
    """
    Safety net: requeue PENDING withdrawals that were never dispatched.

    A withdrawal stays PENDING with an empty track_id when queueing
    process_withdrawal_requests failed (broker down) or the task was dropped
    before it ran. The customer's IRT is already debited at that point, so the
    row must not be left behind. Requeueing is safe because
    process_withdrawal_requests is idempotent — it claims on status and track_id.

    Only PENDING rows are eligible. A withdrawal that reached PROCESSING already
    has its track_id committed (both are written in the same save), so it may
    have been sent to the PSP and must never be blindly resubmitted from here;
    inquiry_processed_withdrawals owns that recovery and resolves it against the
    PSP instead.

    Only rows older than STUCK_WITHDRAWAL_AGE_MINUTES are picked up, so this
    never races with the normal apply_async(countdown=10) path.
    """
    cutoff = timezone.now() - timedelta(minutes=STUCK_WITHDRAWAL_AGE_MINUTES)

    stuck = list(
        Withdrawal.objects.filter(
            status=Withdrawal.WithdrawalStatus.PENDING,
            track_id='',
            created_at__lt=cutoff,
        ).order_by('created_at')[:STUCK_WITHDRAWAL_BATCH_SIZE]
    )

    if not stuck:
        return

    logger.warning(
        f"[task=stuck_withdrawals] Found {len(stuck)} stuck withdrawal(s) — requeuing"
    )

    for withdrawal in stuck:
        process_withdrawal_requests.delay(withdrawal.id)
        logger.info(
            f"[task=stuck_withdrawals] Requeued withdrawal | withdrawal_id={withdrawal.id}"
        )