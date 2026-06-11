"""
Unit Tests — SettlementService
────────────────────────────────
Covers initiate_withdrawal_request.
Real DB is used; Celery task is always mocked.
"""

import pytest
from unittest.mock import MagicMock

from apps.settlements.services.settlement_services import SettlementService
from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.models.wallet import Wallet
from apps.customers.exceptions.bank_card_exceptions import BankCardNotFound
from apps.exchange.exceptions.exchange_exceptions import InsufficientUserBalance

from .conftest import WITHDRAWAL_AMT, WALLET_BALANCE


def _make_request(user):
    """Build a minimal request-like object the service accepts."""
    request = MagicMock()
    request.user = user
    request.META = {'REMOTE_ADDR': '127.0.0.1'}
    return request


# ═════════════════════════════════════════════════════════════════════════════
# initiate_withdrawal_request
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestInitiateWithdrawalRequest:

    def test_invalid_card_id_raises_bank_card_not_found(
        self, user, customer, irt_wallet, mock_withdrawal_task
    ):
        """A card_id that does not belong to the customer must raise BankCardNotFound."""
        with pytest.raises(BankCardNotFound):
            SettlementService.initiate_withdrawal_request(
                amount=WITHDRAWAL_AMT,
                card_id=99999,
                request=_make_request(user),
            )

    def test_insufficient_balance_raises_insufficient_user_balance(
        self, user, customer, bank_card, mock_withdrawal_task
    ):
        """Requesting more than the wallet balance must raise InsufficientUserBalance."""
        # No irt_wallet fixture → balance = 0
        with pytest.raises(InsufficientUserBalance):
            SettlementService.initiate_withdrawal_request(
                amount=WITHDRAWAL_AMT,
                card_id=bank_card.id,
                request=_make_request(user),
            )

    def test_success_creates_withdrawal_row(
        self, user, customer, bank_card, irt_wallet, mock_withdrawal_task
    ):
        """A successful request must persist a Withdrawal with status=pending."""
        assert Withdrawal.objects.count() == 0

        SettlementService.initiate_withdrawal_request(
            amount=WITHDRAWAL_AMT,
            card_id=bank_card.id,
            request=_make_request(user),
        )

        assert Withdrawal.objects.count() == 1
        withdrawal = Withdrawal.objects.first()
        assert withdrawal.amount == WITHDRAWAL_AMT
        assert withdrawal.status == Withdrawal.WithdrawalStatus.PENDING
        assert withdrawal.customer == customer

    def test_success_creates_negative_wallet_entry(
        self, user, customer, bank_card, irt_wallet, mock_withdrawal_task
    ):
        """A successful request must create a debit wallet entry equal to -amount."""
        # Initial wallet has WALLET_BALANCE; after withdrawal there must be an extra
        # negative entry for the withdrawal amount.
        initial_count = Wallet.objects.filter(customer=customer).count()

        SettlementService.initiate_withdrawal_request(
            amount=WITHDRAWAL_AMT,
            card_id=bank_card.id,
            request=_make_request(user),
        )

        assert Wallet.objects.filter(customer=customer).count() == initial_count + 1
        # Filter for the debit entry directly (negative amount)
        debit = Wallet.objects.filter(customer=customer, wallet_type='irt', amount__lt=0).first()
        assert debit is not None
        assert int(debit.amount) == -WITHDRAWAL_AMT

    def test_success_dispatches_celery_task(
        self, user, customer, bank_card, irt_wallet, mock_withdrawal_task
    ):
        """process_withdrawal_requests.apply_async must be called exactly once."""
        SettlementService.initiate_withdrawal_request(
            amount=WITHDRAWAL_AMT,
            card_id=bank_card.id,
            request=_make_request(user),
        )

        mock_withdrawal_task.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# process_stuck_withdrawals
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestProcessStuckWithdrawals:

    @staticmethod
    def _make_withdrawal(customer, bank_card, *, status, track_id='', age_minutes=0):
        """Create a withdrawal and backdate created_at (auto_now_add) via update()."""
        from datetime import timedelta
        from django.utils import timezone

        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=status,
            track_id=track_id,
        )
        if age_minutes:
            Withdrawal.objects.filter(id=withdrawal.id).update(
                created_at=timezone.now() - timedelta(minutes=age_minutes)
            )
        return withdrawal

    def test_old_pending_withdrawal_is_requeued(self, customer, bank_card, mocker):
        """A PENDING withdrawal older than the age threshold must be requeued."""
        from apps.settlements.tasks.settlement_tasks import process_stuck_withdrawals

        delay_mock = mocker.patch(
            'apps.settlements.tasks.settlement_tasks.process_withdrawal_requests.delay'
        )
        withdrawal = self._make_withdrawal(
            customer, bank_card,
            status=Withdrawal.WithdrawalStatus.PENDING,
            age_minutes=10,
        )

        process_stuck_withdrawals()

        delay_mock.assert_called_once_with(withdrawal.id)

    def test_fresh_pending_withdrawal_is_not_requeued(self, customer, bank_card, mocker):
        """A PENDING withdrawal younger than the threshold must be left alone."""
        from apps.settlements.tasks.settlement_tasks import process_stuck_withdrawals

        delay_mock = mocker.patch(
            'apps.settlements.tasks.settlement_tasks.process_withdrawal_requests.delay'
        )
        self._make_withdrawal(
            customer, bank_card,
            status=Withdrawal.WithdrawalStatus.PENDING,
            age_minutes=0,
        )

        process_stuck_withdrawals()

        delay_mock.assert_not_called()

    def test_pending_with_track_id_is_not_requeued(self, customer, bank_card, mocker):
        """A withdrawal that already reached the PSP (has track_id) must not be requeued."""
        from apps.settlements.tasks.settlement_tasks import process_stuck_withdrawals

        delay_mock = mocker.patch(
            'apps.settlements.tasks.settlement_tasks.process_withdrawal_requests.delay'
        )
        self._make_withdrawal(
            customer, bank_card,
            status=Withdrawal.WithdrawalStatus.PENDING,
            track_id='123',
            age_minutes=10,
        )

        process_stuck_withdrawals()

        delay_mock.assert_not_called()

    def test_non_pending_statuses_are_not_requeued(self, customer, bank_card, mocker):
        """SENT_TO_BANK / COMPLETED / FAILED rows must never be requeued."""
        from apps.settlements.tasks.settlement_tasks import process_stuck_withdrawals

        delay_mock = mocker.patch(
            'apps.settlements.tasks.settlement_tasks.process_withdrawal_requests.delay'
        )
        for status in (
            Withdrawal.WithdrawalStatus.SENT_TO_BANK,
            Withdrawal.WithdrawalStatus.COMPLETED,
            Withdrawal.WithdrawalStatus.FAILED,
        ):
            self._make_withdrawal(
                customer, bank_card, status=status, age_minutes=10,
            )

        process_stuck_withdrawals()

        delay_mock.assert_not_called()
