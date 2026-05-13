from django.db import transaction
from celery import shared_task
from django.utils import timezone

from apps.payments.models.invoice import Invoice
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.exchange.models.currency import Currency
from apps.core.utils.date_time_utils import get_date_time


@shared_task(bind=True, max_retries=3)
def process_deposit_invoice_task(self, invoice_id):
    try:
        now_ts = get_date_time()['timestamp']

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            # Idempotency check
            if invoice.is_processed:
                return f"Invoice {invoice_id} already processed"
            
            # Create wallet entry    
            Wallet.objects.create(
                customer=invoice.customer,
                wallet_type=Wallet.WALLETTYPES[0][0],  # IRT
                amount=invoice.total_price,
                desc=f"شارژ کیف پول به شماره فاکتور: {invoice.id}",
                verified_at=now_ts,
                created_at=now_ts,
                is_verified=True,
            )
            
            # Mark invoice as processed
            invoice.is_processed = True
            invoice.processed_at = timezone.now()
            invoice.save(update_fields=['is_processed', 'processed_at'])
            
        return f"Wallet charged successfully for invoice {invoice_id}"
        
    except Exception as exc:
        # Retry with backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def process_buy_invoice_task(self, invoice_id):
    try:

        now_ts = get_date_time()['timestamp']

        currency = Currency.objects.get(symbol='XAU18')  # Assuming gold purchase for simplicity

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            if invoice.is_processed:
                return f"Invoice {invoice_id} already processed"
            
            total_price = invoice.total_price - (invoice.fee + invoice.maintenance_fee)

            # Create transaction record for the asset purchase
            Transaction.objects.create(
                customer=invoice.customer,
                invoice=invoice,
                currency=currency,
                amount=total_price / invoice.unit_price,  # Calculate amount based on unit price
                fee_irt=invoice.fee,
                unit_price_irt=invoice.unit_price,
                total_price_irt=invoice.total_price,
                transaction_type=Transaction.TRANSACTIONTYPES[0][0],  # buy
                status=Transaction.TRANSACTIONSTATUSES[0][0],  # pending
                deposit_method=Transaction.DEPOSITTYPES[1][0],  # gate
                created_at=now_ts,
            )
            
            # Mark invoice as processed
            invoice.is_processed = True
            invoice.processed_at = timezone.now()
            invoice.save(update_fields=['is_processed', 'processed_at'])
            
        return f"Asset purchase created for invoice {invoice_id}"
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task()
def process_stuck_invoices():
    """
    Safety net: Process invoices that are marked as paid but not processed after a certain time threshold (e.g., 3 minutes).
    """
    stuck_invoices = Invoice.objects.filter(
        is_paid=True,
        is_processed=False
    )
    
    for invoice in stuck_invoices:
        if invoice.invoice_type == Invoice.INVOICE_TYPES[0][0]:  # deposit
            process_deposit_invoice_task.delay(invoice.id)
        elif invoice.invoice_type == Invoice.INVOICE_TYPES[1][0]:  # buy
            process_buy_invoice_task.delay(invoice.id)
