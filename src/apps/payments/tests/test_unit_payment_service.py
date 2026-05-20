"""
Unit Tests — PaymentService
────────────────────────────
Gateway, tasks, and DB selectors are mocked.
Only the service business logic is exercised.
"""

import pytest
from unittest.mock import MagicMock, patch
from django.test import RequestFactory

from apps.payments.services.payments_services import PaymentService
from apps.payments.models.invoice import Invoice
from apps.payments.exceptions.payments_exceptions import InvoiceNotFound

from .conftest import AUTHORITY, CARD_HASH, CARD_NUMBER, CARD_PAN


# ═════════════════════════════════════════════════════════════════════════════
# create_invoice
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreateInvoice:

    def test_creates_invoice_with_correct_fields(self, customer):
        invoice = PaymentService.create_invoice(
            customer=customer,
            total_price=500_000,
            fee=5_000,
        )
        assert invoice.pk is not None
        assert invoice.total_price == 500_000
        assert invoice.fee == 5_000
        assert invoice.status == Invoice.STATUS_CHOICES[0][0]  # pending
        assert invoice.is_paid is False

    def test_default_invoice_type_is_deposit(self, customer):
        invoice = PaymentService.create_invoice(customer=customer, total_price=200_000)
        assert invoice.invoice_type == Invoice.INVOICE_TYPES[0][0]  # deposit


# ═════════════════════════════════════════════════════════════════════════════
# handle_zarinpal_callback
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestHandleZarinpalCallback:

    def _make_request(self):
        return RequestFactory().post('/')

    def test_invoice_not_found_raises(self, mocker):
        mocker.patch(
            'apps.payments.services.payments_services.PaymentsSelectors.get_invoice_by_authority',
            return_value=None,
        )
        with pytest.raises(InvoiceNotFound):
            PaymentService.handle_zarinpal_callback('UNKNOWN-AUTHORITY', self._make_request())

    def test_already_paid_invoice_returns_idempotent_message(self, invoice):
        invoice.is_paid = True
        invoice.save()
        result = PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        assert 'قبلاً' in result['message'] or 'paid' in result['message'].lower()

    def test_verify_101_returns_idempotent_message(
        self, invoice, mock_gateway_verify_101
    ):
        result = PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        assert result is not None
        assert 'message' in result

    def test_verify_102_marks_invoice_as_failed(
        self, invoice, mock_gateway_verify_102
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        invoice.refresh_from_db()
        assert invoice.status == Invoice.STATUS_CHOICES[2][0]  # failed

    def test_matching_card_hash_marks_invoice_as_paid(
        self, invoice, bank_card, mock_gateway_verify_valid_hash, mock_task_deposit
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        invoice.refresh_from_db()
        assert invoice.is_paid is True
        assert invoice.status == Invoice.STATUS_CHOICES[1][0]  # paid

    def test_matching_card_pan_marks_invoice_as_paid(
        self, invoice, bank_card, mock_gateway_verify_valid_pan, mock_task_deposit
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        invoice.refresh_from_db()
        assert invoice.is_paid is True
        assert invoice.status == Invoice.STATUS_CHOICES[1][0]  # paid

    def test_invalid_card_marks_invoice_as_rejected(
        self, invoice, bank_card, mock_gateway_verify_invalid_card, mock_task_deposit
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        invoice.refresh_from_db()
        assert invoice.is_paid is False
        assert invoice.status == Invoice.STATUS_CHOICES[3][0]  # rejected

    def test_deposit_invoice_queues_deposit_task(
        self, invoice, bank_card, mock_gateway_verify_valid_hash, mock_task_deposit
    ):
        PaymentService.handle_zarinpal_callback(AUTHORITY, self._make_request())
        mock_task_deposit.assert_called_once()
        call_kwargs = mock_task_deposit.call_args
        assert invoice.id in call_kwargs[1].get('args', call_kwargs[0][0] if call_kwargs[0] else [])

    def test_buy_invoice_queues_buy_task(
        self, buy_invoice, bank_card, mock_gateway_verify_valid_hash, mock_task_buy
    ):
        buy_invoice.gateway_track_id = 'BUY-AUTHORITY-00000000000001'
        buy_invoice.save()
        PaymentService.handle_zarinpal_callback(
            'BUY-AUTHORITY-00000000000001', self._make_request()
        )
        mock_task_buy.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# initiate_deposit
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestInitiateDeposit:

    def _make_request(self, user):
        request = RequestFactory().post('/')
        request.user = user
        return request

    def test_creates_invoice_and_returns_payment_link(
        self, user, customer, mock_gateway_process
    ):
        result = PaymentService.initiate_deposit(
            amount=500_000,
            request=self._make_request(user),
        )
        assert 'message' in result
        assert 'zarinpal.com' in result['message']
        assert Invoice.objects.filter(customer=customer).exists()

    def test_gateway_failure_marks_invoice_failed_and_reraises(
        self, user, customer, mocker
    ):
        from apps.core.exceptions.base import PaymentGatewayError
        mocker.patch(
            'apps.payments.services.payments_services.PaymentService.gateway.process_payment',
            side_effect=PaymentGatewayError('gateway down'),
        )
        with pytest.raises(PaymentGatewayError):
            PaymentService.initiate_deposit(
                amount=500_000,
                request=self._make_request(user),
            )
        invoice = Invoice.objects.filter(customer=customer).first()
        assert invoice is not None
        assert invoice.status == 'failed'
        assert invoice.gateway_response == 'gateway_failed'
