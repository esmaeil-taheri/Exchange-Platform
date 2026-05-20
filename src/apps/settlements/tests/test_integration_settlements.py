"""
Integration Tests — settlements
─────────────────────────────────
Real DB transactions.  Verifies that withdrawal creation produces correct
persistent state end-to-end.
"""

import pytest
from django.db.models import Sum

from apps.settlements.services.settlement_services import SettlementService
from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.models.wallet import Wallet
from apps.exchange.exceptions.exchange_exceptions import InsufficientUserBalance

from .conftest import WITHDRAWAL_AMT, WALLET_BALANCE
from unittest.mock import MagicMock


def _make_request(user):
    request = MagicMock()
    request.user = user
    request.META = {'REMOTE_ADDR': '127.0.0.1'}
    return request


# ═════════════════════════════════════════════════════════════════════════════
# End-to-end withdrawal state
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestWithdrawalIntegration:

    def test_withdrawal_persisted_and_wallet_debited(
        self, user, customer, bank_card, irt_wallet, mock_withdrawal_task
    ):
        """
        After a successful withdrawal request:
          - One Withdrawal row must exist with status=pending
          - The net IRT balance must equal WALLET_BALANCE - WITHDRAWAL_AMT
        """
        SettlementService.initiate_withdrawal_request(
            amount=WITHDRAWAL_AMT,
            card_id=bank_card.id,
            request=_make_request(user),
        )

        # Withdrawal persisted
        assert Withdrawal.objects.filter(customer=customer).count() == 1
        withdrawal = Withdrawal.objects.get(customer=customer)
        assert withdrawal.status == Withdrawal.WithdrawalStatus.PENDING
        assert withdrawal.amount == WITHDRAWAL_AMT
        assert withdrawal.remaining_wallet_amount == WALLET_BALANCE - WITHDRAWAL_AMT

        # Wallet debited
        net = Wallet.objects.filter(
            customer=customer, wallet_type='irt', is_verified=True
        ).aggregate(total=Sum('amount'))['total']
        assert int(net) == WALLET_BALANCE - WITHDRAWAL_AMT

    def test_second_request_exceeding_remaining_balance_is_blocked(
        self, user, customer, bank_card, irt_wallet, mock_withdrawal_task
    ):
        """
        After the first withdrawal has consumed most of the balance, a second
        request for an amount larger than the remaining balance must be rejected
        with InsufficientUserBalance.
        """
        # First request: leaves WALLET_BALANCE - WITHDRAWAL_AMT = 500,000
        SettlementService.initiate_withdrawal_request(
            amount=WITHDRAWAL_AMT,
            card_id=bank_card.id,
            request=_make_request(user),
        )

        # Second request: 600,000 > 500,000 remaining → must fail
        with pytest.raises(InsufficientUserBalance):
            SettlementService.initiate_withdrawal_request(
                amount=600_000,
                card_id=bank_card.id,
                request=_make_request(user),
            )

        # Only the first withdrawal must exist
        assert Withdrawal.objects.filter(customer=customer).count() == 1
