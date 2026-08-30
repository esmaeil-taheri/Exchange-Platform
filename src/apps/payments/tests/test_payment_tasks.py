from decimal import Decimal
import pytest
from django.utils import timezone

from apps.exchange.models.currency import Currency
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.payments.models.invoice import Invoice
from apps.payments.tasks.payment_tasks import (
    process_deposit_invoice_task,
    process_buy_invoice_task,
    process_stuck_invoices,
)


@pytest.fixture
def currency_xau(db):
    return Currency.objects.get_or_create(
        symbol='XAU18',
        defaults={
            'fa_title': 'طلا ۱۸ عیار',
            'en_title': 'Gold 18k',
            'is_buy': True,
            'is_sell': True,
        }
    )[0]


@pytest.mark.django_db
class TestProcessDepositInvoiceTask:

    def test_process_deposit_invoice_success(self, customer, invoice):
        res = process_deposit_invoice_task(invoice.id)
        assert "Wallet charged successfully" in res

        invoice.refresh_from_db()
        assert invoice.is_processed is True
        assert invoice.processed_at is not None

        wallet = Wallet.objects.filter(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],  # irt
            amount=invoice.total_price,
        ).first()
        assert wallet is not None
        assert wallet.is_verified is True

    def test_process_deposit_invoice_idempotency(self, customer, invoice):
        # First execution
        res1 = process_deposit_invoice_task(invoice.id)
        assert "Wallet charged successfully" in res1

        # Second execution
        res2 = process_deposit_invoice_task(invoice.id)
        assert "already processed" in res2

        # Verify only one wallet entry was created
        wallet_count = Wallet.objects.filter(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=invoice.total_price,
        ).count()
        assert wallet_count == 1


@pytest.mark.django_db
class TestProcessBuyInvoiceTask:

    def test_process_buy_invoice_success_decimal_precision(self, customer, buy_invoice, currency_xau):
        # buy_invoice has total_price=5_000_000, unit_price=1_000_000, fee=50_000, maintenance_fee=10_000
        # total_net = 5_000_000 - 60_000 = 4_940_000
        # gold_amount = 4.9400
        res = process_buy_invoice_task(buy_invoice.id)
        assert "Asset purchase created" in res

        buy_invoice.refresh_from_db()
        assert buy_invoice.is_processed is True
        assert buy_invoice.processed_at is not None

        txn = Transaction.objects.filter(invoice=buy_invoice).first()
        assert txn is not None
        assert txn.customer == customer
        assert txn.currency == currency_xau
        assert txn.amount == Decimal("4.9400")
        assert txn.total_price_irt == buy_invoice.total_price
        assert txn.fee_irt == buy_invoice.fee
        assert txn.unit_price_irt == buy_invoice.unit_price
        assert txn.transaction_type == Transaction.TRANSACTIONTYPES[0][0]  # buy
        assert txn.status == Transaction.TRANSACTIONSTATUSES[0][0]        # pending
        assert txn.deposit_method == Transaction.DEPOSITTYPES[1][0]       # gate

    def test_process_buy_invoice_idempotency(self, customer, buy_invoice, currency_xau):
        res1 = process_buy_invoice_task(buy_invoice.id)
        assert "Asset purchase created" in res1

        res2 = process_buy_invoice_task(buy_invoice.id)
        assert "already processed" in res2

        txn_count = Transaction.objects.filter(invoice=buy_invoice).count()
        assert txn_count == 1


@pytest.mark.django_db
class TestProcessStuckInvoices:

    def test_process_stuck_invoices_requeues(self, customer, mocker):
        mock_deposit = mocker.patch(
            "apps.payments.tasks.payment_tasks.process_deposit_invoice_task.delay"
        )
        mock_buy = mocker.patch(
            "apps.payments.tasks.payment_tasks.process_buy_invoice_task.delay"
        )

        stuck_deposit = Invoice.objects.create(
            customer=customer,
            total_price=200_000,
            is_paid=True,
            is_processed=False,
            invoice_type=Invoice.INVOICE_TYPES[0][0],  # deposit
        )
        stuck_buy = Invoice.objects.create(
            customer=customer,
            total_price=2_000_000,
            unit_price=1_000_000,
            is_paid=True,
            is_processed=False,
            invoice_type=Invoice.INVOICE_TYPES[1][0],  # buy
        )

        # Non-stuck invoice (already processed)
        Invoice.objects.create(
            customer=customer,
            total_price=300_000,
            is_paid=True,
            is_processed=True,
            invoice_type=Invoice.INVOICE_TYPES[0][0],
        )

        process_stuck_invoices()

        mock_deposit.assert_called_once_with(stuck_deposit.id)
        mock_buy.assert_called_once_with(stuck_buy.id)
