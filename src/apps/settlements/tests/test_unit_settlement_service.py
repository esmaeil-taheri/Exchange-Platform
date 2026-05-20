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
