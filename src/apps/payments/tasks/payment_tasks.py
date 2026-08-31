from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from celery import shared_task
from django.utils import timezone

from apps.payments.models.invoice import Invoice
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.exchange.models.currency import Currency
from apps.core.utils.date_time_utils import get_date_time

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_deposit_invoice_task(self, invoice_id):
    logger.info(f"[task=process_deposit] Processing deposit invoice | invoice_id={invoice_id}")
    try:
        now_ts = get_date_time()['timestamp']

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)

            if invoice.is_processed:
                logger.info(
                    f"[task=process_deposit] Invoice already processed — skipped | invoice_id={invoice_id}"
                )
                return f"Invoice {invoice_id} already processed"

            Wallet.objects.create(
                customer=invoice.customer,
                wallet_type=Wallet.WALLETTYPES[0][0],
                amount=invoice.total_price,
                desc=f"شارژ کیف پول به شماره فاکتور: {invoice.id}",
                verified_at=now_ts,
                created_at=now_ts,
                is_verified=True,
            )

            invoice.is_processed = True
            invoice.processed_at = timezone.now()
            invoice.save(update_fields=['is_processed', 'processed_at'])

        logger.info(
            f"[task=process_deposit] IRT wallet credited | invoice_id={invoice_id} "
            f"customer_id={invoice.customer_id} amount={invoice.total_price}IRT"
        )
        return f"Wallet charged successfully for invoice {invoice_id}"

    except Exception as exc:
        logger.error(
            f"[task=process_deposit] Failed — retrying | invoice_id={invoice_id} "
            f"attempt={self.request.retries + 1} error={exc}"
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def process_buy_invoice_task(self, invoice_id):
    logger.info(f"[task=process_buy] Processing buy invoice | invoice_id={invoice_id}")
    try:
        now_ts = get_date_time()['timestamp']
        currency = Currency.objects.get(symbol='XAU18')

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)

            if invoice.is_processed:
                logger.info(
                    f"[task=process_buy] Invoice already processed — skipped | invoice_id={invoice_id}"
                )
                return f"Invoice {invoice_id} already processed"

            # The invoice does not store the quoted gold amount, so it is rebuilt
            # here by inverting the quote. PriceService rounds gold_price_toman
            # with ROUND_HALF_UP, so this division must use ROUND_HALF_UP too —
            # ROUND_DOWN loses 0.0001g whenever that rounding went down, and the
            # buy worker then rejects the transaction on an exact total mismatch.
            total_price = invoice.total_price - (invoice.fee + invoice.maintenance_fee)
            gold_amount = (Decimal(str(total_price)) / Decimal(str(invoice.unit_price))).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )

            txn = Transaction.objects.create(
                customer=invoice.customer,
                invoice=invoice,
                currency=currency,
                amount=gold_amount,
                fee_irt=invoice.fee,
                unit_price_irt=invoice.unit_price,
                total_price_irt=invoice.total_price,
                transaction_type=Transaction.TRANSACTIONTYPES[0][0],
                status=Transaction.TRANSACTIONSTATUSES[0][0],
                deposit_method=Transaction.DEPOSITTYPES[1][0],
                created_at=now_ts,
            )

            invoice.is_processed = True
            invoice.processed_at = timezone.now()
            invoice.save(update_fields=['is_processed', 'processed_at'])

        logger.info(
            f"[task=process_buy] Buy transaction created | invoice_id={invoice_id} "
            f"transaction_id={txn.id} customer_id={invoice.customer_id} amount={txn.amount}g"
        )
        return f"Asset purchase created for invoice {invoice_id}"

    except Exception as exc:
        logger.error(
            f"[task=process_buy] Failed — retrying | invoice_id={invoice_id} "
            f"attempt={self.request.retries + 1} error={exc}"
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task()
def process_stuck_invoices():
    """Safety net: Process invoices paid but not processed."""
    stuck_invoices = Invoice.objects.filter(is_paid=True, is_processed=False)
    count = stuck_invoices.count()

    if count:
        logger.warning(f"[task=stuck_invoices] Found {count} stuck invoice(s) — requeuing")

    for invoice in stuck_invoices:
        if invoice.invoice_type == Invoice.INVOICE_TYPES[0][0]:
            process_deposit_invoice_task.delay(invoice.id)
            logger.info(f"[task=stuck_invoices] Requeued deposit invoice | invoice_id={invoice.id}")
        elif invoice.invoice_type == Invoice.INVOICE_TYPES[1][0]:
            process_buy_invoice_task.delay(invoice.id)
            logger.info(f"[task=stuck_invoices] Requeued buy invoice | invoice_id={invoice.id}")
