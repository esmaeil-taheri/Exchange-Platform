"""
Integration Tests — payments
──────────────────────────────
Real DB and real transactions are used.
Gateway and Celery tasks are mocked (external services).
"""

import pytest
from django.test import RequestFactory

from apps.payments.services.payments_services import PaymentService
from apps.payments.models.invoice import Invoice

from .conftest import AUTHORITY


def _make_request():
    return RequestFactory().post('/')


# ═════════════════════════════════════════════════════════════════════════════
# Invoice Creation
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestInvoiceCreation:

    def test_invoice_persisted_with_correct_fields(self, customer):
        invoice = PaymentService.create_invoice(
            customer=customer,
            total_price=750_000,
            fee=7_500,
            maintenance_fee=1_500,
            invoice_type=Invoice.INVOICE_TYPES[0][0],
        )

        saved = Invoice.objects.get(pk=invoice.pk)
        assert saved.total_price == 750_000
        assert saved.fee == 7_500
        assert saved.maintenance_fee == 1_500
        assert saved.status == Invoice.STATUS_CHOICES[0][0]   # pending
        assert saved.is_paid is False
        assert saved.is_processed is False


# ═════════════════════════════════════════════════════════════════════════════
# Zarinpal Callback — DB state after callback
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestZarinpalCallbackIntegration:

    def test_invoice_status_updated_to_paid_in_db(
        self, invoice, bank_card, mock_gateway_verify_valid_hash, mock_task_deposit
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, _make_request())

        invoice.refresh_from_db()
        assert invoice.is_paid is True
        assert invoice.status == Invoice.STATUS_CHOICES[1][0]   # paid
        assert invoice.ref_id == '99999'

    def test_second_callback_after_payment_raises_not_found(
        self, invoice, bank_card, mock_gateway_verify_valid_hash, mock_task_deposit
    ):
        """
        After a successful callback the invoice status changes from 'pending' to 'paid'.
        The selector only returns pending invoices, so a second callback raises InvoiceNotFound
        (the invoice is no longer discoverable via authority lookup).
        """
        from apps.payments.exceptions.payments_exceptions import InvoiceNotFound

        PaymentService.handle_zarinpal_callback(AUTHORITY, _make_request())

        invoice.refresh_from_db()
        assert invoice.is_paid is True  # first call succeeded

        with pytest.raises(InvoiceNotFound):
            PaymentService.handle_zarinpal_callback(AUTHORITY, _make_request())


# ═════════════════════════════════════════════════════════════════════════════
# Deposit Flow — end-to-end invoice creation
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDepositIntegration:

    def test_invoice_created_in_db_after_initiate_deposit(
        self, user, customer, mock_gateway_process
    ):
        request = RequestFactory().post('/')
        request.user = user

        assert not Invoice.objects.filter(customer=customer).exists()

        PaymentService.initiate_deposit(amount=300_000, request=request)

        invoices = Invoice.objects.filter(customer=customer)
        assert invoices.count() == 1
        assert invoices.first().total_price == 300_000
        assert invoices.first().invoice_type == Invoice.INVOICE_TYPES[0][0]  # deposit
        assert invoices.first().gateway_track_id == AUTHORITY
