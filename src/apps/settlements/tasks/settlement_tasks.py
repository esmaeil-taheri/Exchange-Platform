from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.settlements.models.withdrawal import Withdrawal
from apps.core.services.settlement.vandar import VandarClient
from apps.exchange.models.wallet import Wallet
from apps.core.utils.date_time_utils import get_date_time

import logging


logger = logging.getLogger(__name__)


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
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)

        if withdrawal.status != Withdrawal.WithdrawalStatus.PENDING:
            return f"Withdrawal {withdrawal_id} already processed"

        if withdrawal.track_id:
            return f"Withdrawal {withdrawal_id} already has track_id"

        customer = withdrawal.customer
        card = withdrawal.card
        
        track_id = str(withdrawal.id)

        iban = card.Shaba_number
        national_code = customer.user.national_id
        birth_date = customer.birth_date

        response = vandar.create_settlement(
            amount=withdrawal.amount - vandar.wage,
            iban=iban,
            track_id=track_id,
            payment_number=str(withdrawal.id),
            description=f"withdrawal #{withdrawal.id}",
            national_code=national_code,
            birth_date=birth_date,
        )

        with transaction.atomic():

            withdrawal = Withdrawal.objects.select_for_update().get(id=withdrawal_id)

            if withdrawal.status != Withdrawal.WithdrawalStatus.PENDING:
                return f"Withdrawal {withdrawal_id} already updated"
            
            if response.get("error"):

                error_message = response.get("message", "Unknown PSP error")

                now_ts = get_date_time()['timestamp']

                withdrawal.status = Withdrawal.WithdrawalStatus.FAILED
                withdrawal.errors = error_message
                withdrawal.save(update_fields=["status", "errors"])

                Wallet.objects.create(
                    customer=withdrawal.customer,
                    wallet_type='irt',
                    amount=withdrawal.amount,
                    desc=f'برگشت وجه بابت شکست تسویه — درخواست برداشت #{withdrawal.id}',
                    ip='system',
                    created_at=now_ts,
                    verified_at=now_ts,
                    is_verified=True,
                )

                logger.error(
                    f"[task=process_withdrawal] Settlement FAILED — IRT refunded | "
                    f"withdrawal_id={withdrawal_id} customer_id={withdrawal.customer_id} "
                    f"amount={withdrawal.amount}IRT reason={error_message}"
                )

                return f"PSP Error: {error_message}"

            settlement = response["data"]["settlement"][0]

            withdrawal.track_id = track_id
            withdrawal.transaction_id = str(settlement.get("transaction_id"))
            withdrawal.vandar_amount = settlement.get("amount")
            withdrawal.wage = settlement.get("wage_toman", 0)
            withdrawal.vandar_status = settlement.get("status")
            withdrawal.iban = settlement.get("iban")
            withdrawal.desc = settlement.get("description")
            withdrawal.settlement_date = settlement.get("settlement_date")
            withdrawal.settlement_time = settlement.get("settlement_time")
            withdrawal.is_instant = settlement.get("is_instant")

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

    pendings = Withdrawal.objects.filter(
        status=Withdrawal.WithdrawalStatus.SENT_TO_BANK
    ).order_by("created_at")[:5]

    if not pendings:
        return

    vandar = VandarClient(token=token, business=business)

    for pending in pendings:

        try:

            withdrawal = Withdrawal.objects.get(id=pending.id)

            if withdrawal.status != Withdrawal.WithdrawalStatus.SENT_TO_BANK:
                continue

            response = vandar.inquiry_settlement(withdrawal.track_id)

            if response.get("error"):
                withdrawal.errors = response.get("message")
                withdrawal.save(update_fields=["errors"])
                continue

            settlement = response["data"]["settlements"][0]
            status = settlement.get("status")

            with transaction.atomic():

                withdrawal = Withdrawal.objects.select_for_update().get(id=pending.id)

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
                        ip='system',
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


STUCK_WITHDRAWAL_AGE_MINUTES = 5
STUCK_WITHDRAWAL_BATCH_SIZE = 20


@shared_task()
def process_stuck_withdrawals():
    """
    Safety net: requeue PENDING withdrawals whose processing task was lost.

    A withdrawal stays PENDING with an empty track_id if queueing
    process_withdrawal_requests failed (broker down) or the task was dropped.
    The user's IRT is already debited at that point, so the row must not be
    left behind. Requeueing is safe because process_withdrawal_requests is
    idempotent (it checks both status and track_id before doing anything).

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