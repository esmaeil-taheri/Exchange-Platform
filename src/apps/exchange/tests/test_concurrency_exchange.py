"""
Concurrency Tests — ExchangeService order registration
────────────────────────────────────────────────────────
Covers the customer-row-lock guards added against TOCTOU races
(pending-transaction and daily-limit checks moved inside the lock).

The TestRaceGuards class runs everywhere (it checks the guard logic and its
placement, not lock semantics). The TestRealRowLocks class needs real
SELECT ... FOR UPDATE blocking, which SQLite silently ignores, so it only
runs against PostgreSQL (e.g. inside docker compose).
"""

import threading
from decimal import Decimal

import pytest
from unittest.mock import MagicMock

from django.db import connection, connections

from apps.exchange.services.exchange_services import ExchangeService
from apps.exchange.models.transaction import Transaction
from apps.payments.models.invoice import Invoice
from apps.core.exceptions.base import ActionDisabled

from .conftest import BUY_IRT_AMT


def _make_request(user):
    req = MagicMock()
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


# ═════════════════════════════════════════════════════════════════════════════
# Guard placement (runs on any database)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestRaceGuards:

    def test_gateway_buy_with_pending_transaction_creates_no_invoice(
        self, user, customer, bank_card, mock_site_settings, mock_price_buy,
        mock_daily_limit, currency
    ):
        """
        The pending-transaction guard must fire before the invoice is created,
        otherwise a raced request would leave an orphan payable invoice behind.
        """
        Transaction.objects.create(
            customer=customer,
            currency=currency,
            status='pending',
            amount=Decimal('0.0560'),
            ip='127.0.0.1',
            created_at=1_000_000,
        )

        with pytest.raises(ActionDisabled):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=BUY_IRT_AMT, buy_from_wallet=False
            )

        assert Invoice.objects.count() == 0

    def test_suspended_customer_blocked_on_gateway_path_too(
        self, user, customer, bank_card, mock_site_settings, mock_price_buy,
        mock_daily_limit, currency
    ):
        """The suspension guard now lives inside the lock; gateway path must still enforce it."""
        from apps.customers.exceptions.customer_exceptions import CustomerSuspended

        customer.status = 'suspended'
        customer.save(update_fields=['status'])

        with pytest.raises(CustomerSuspended):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=BUY_IRT_AMT, buy_from_wallet=False
            )

        assert Invoice.objects.count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# Real row-lock semantics (PostgreSQL only)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='needs real SELECT FOR UPDATE blocking; SQLite ignores row locks',
)
@pytest.mark.django_db(transaction=True)
class TestRealRowLocks:

    def test_concurrent_wallet_buys_yield_single_pending_transaction(
        self, user, authenticated_customer, currency, price_log,
        currency_balance, daily_limit, site_settings, irt_wallet
    ):
        """
        Two simultaneous wallet buys from the same user: the customer row lock
        must serialize them, so the second one sees the first one's pending
        transaction and is rejected with ActionDisabled.
        """
        errors = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                barrier.wait()
                ExchangeService.buy_asset(
                    _make_request(user), 'XAU18', BUY_IRT_AMT, True
                )
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                for conn in connections.all():
                    conn.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert Transaction.objects.filter(
            customer=authenticated_customer, status='pending'
        ).count() == 1
        assert errors == ['ActionDisabled']
