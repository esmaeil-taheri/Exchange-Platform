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
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.settlements.services.settlement_services import SettlementService
from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.core.models.idempotency import IdempotencyRecord
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

    def test_concurrent_withdrawals_cannot_overdraw_the_irt_wallet(
        self, user, authenticated_customer, irt_wallet, bank_card, mocker
    ):
        """
        WalletSelector.get_user_balance_under_customer_lock does not lock — the
        `select_for_update()` it used to carry was dropped by Django's aggregate
        path, so the emitted SQL is a plain SELECT SUM(...). What actually
        prevents an overdraft is the Customer row lock that every debit path
        holds across both the balance check and the debit.

        Two simultaneous withdrawals isolate exactly that guarantee: unlike two
        buys, nothing else serializes them — there is no pending-transaction
        rule on this path. Each asks for 70% of the balance. Serialized, one
        succeeds and the other is rejected. Unserialized, both read the same
        balance, both pass their check, and the ledger goes negative.
        """
        mocker.patch(
            'apps.settlements.services.settlement_services.'
            'process_withdrawal_requests.apply_async',
            return_value=None,
        )

        balance = WalletSelector.get_user_balance_under_customer_lock(
            user_id=user.id, wallet_type='irt'
        )
        each = int(balance * Decimal('0.7'))
        assert each * 2 > balance, 'test is meaningless unless the two overlap'

        errors = []
        barrier = threading.Barrier(2)

        def withdraw():
            try:
                barrier.wait()
                SettlementService.initiate_withdrawal_request(
                    each, bank_card.id, _make_request(user)
                )
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                for conn in connections.all():
                    conn.close()

        threads = [threading.Thread(target=withdraw) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = WalletSelector.get_user_balance_under_customer_lock(
            user_id=user.id, wallet_type='irt'
        )
        assert final >= 0, f'IRT wallet overdrawn to {final}'
        assert Withdrawal.objects.filter(customer=authenticated_customer).count() == 1
        assert errors == ['InsufficientUserBalance']

    def test_simultaneous_sells_sharing_one_idempotency_key_settle_once(
        self, user, authenticated_customer, currency, price_log,
        daily_limit, site_settings, xau_wallet
    ):
        """
        Two requests fire at once carrying the same key — the double-submit a
        retrying mobile client actually produces.

        Nothing in the application layer arbitrates this. The loser of the
        INSERT blocks on the unique index until the winner commits, then reads
        the committed row and replays it. That is the whole mechanism, and it
        is why the resolution is a unique constraint rather than an
        `if exists()` — a check-then-insert has a window here, and this test
        would land in it.

        Note what the loser does NOT hit: the pending-transaction guard. It
        never reaches the customer lock, because the key is claimed first.
        """
        results = []
        errors = []
        barrier = threading.Barrier(2)
        key = 'c0ffee00-dead-4bee-8fad-0123456789ab'

        def sell():
            try:
                barrier.wait()
                results.append(
                    ExchangeService.sell_asset(
                        _make_request(user), 'XAU18', Decimal('0.0500'), False,
                        idempotency_key=key,
                    )
                )
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                for conn in connections.all():
                    conn.close()

        threads = [threading.Thread(target=sell) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f'no request should fail, got {errors}'
        assert len(results) == 2
        assert results[0] == results[1], 'both callers must get the same answer'

        assert Transaction.objects.filter(
            customer=authenticated_customer, transaction_type='sell'
        ).count() == 1
        assert Wallet.objects.filter(
            customer=authenticated_customer, wallet_type='xau', amount__lt=0
        ).count() == 1
        assert IdempotencyRecord.objects.filter(key=key).count() == 1

        final = WalletSelector.get_user_balance_under_customer_lock(
            user_id=user.id, wallet_type='xau'
        )
        assert final == Decimal('1.0000') - Decimal('0.0500')
