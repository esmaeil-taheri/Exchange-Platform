"""
Unit and Task Tests — Settlement Tasks
──────────────────────────────────────
Verifies process_withdrawal_requests and inquiry_processed_withdrawals.
Specifically tests timeout and network error handling to guarantee no double payout.
"""

import pytest
from unittest.mock import MagicMock
from django.utils import timezone

from apps.settlements.models.withdrawal import Withdrawal
from apps.exchange.models.wallet import Wallet
from apps.settlements.tasks.settlement_tasks import (
    process_withdrawal_requests,
    inquiry_processed_withdrawals,
)
from .conftest import WITHDRAWAL_AMT


@pytest.mark.django_db(transaction=True)
class TestProcessWithdrawalRequests:

    def _create_pending_withdrawal(self, customer, bank_card):
        return Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.PENDING,
            track_id='',
        )

    def test_timeout_does_not_refund_wallet_and_marks_for_inquiry(
        self, customer, bank_card, mocker
    ):
        """
        CRITICAL TEST (Task 1.1):
        When Vandar times out, the system must NOT mark FAILED and must NOT refund the wallet.
        It must set status=SENT_TO_BANK with track_id so inquiry can verify later.
        """
        withdrawal = self._create_pending_withdrawal(customer, bank_card)
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        mock_instance.create_settlement.return_value = {
            "error": True,
            "is_timeout": True,
            "is_definitive_failure": False,
            "message": "Request timed out",
        }
        mock_vandar.return_value = mock_instance

        result = process_withdrawal_requests(withdrawal.id)

        withdrawal.refresh_from_db()
        # Status must be SENT_TO_BANK (not FAILED)
        assert withdrawal.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK
        assert withdrawal.track_id == str(withdrawal.id)
        assert withdrawal.bank_send is True
        assert "Unconfirmed PSP state" in withdrawal.errors
        # MUST NOT create any refund wallet row
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count
        assert "PSP Unconfirmed" in result

    def test_network_connection_error_does_not_refund_wallet(
        self, customer, bank_card, mocker
    ):
        """
        When connection to PSP fails unexpectedly, no wallet refund must be issued.
        """
        withdrawal = self._create_pending_withdrawal(customer, bank_card)
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        mock_instance.create_settlement.return_value = {
            "error": True,
            "is_network_error": True,
            "is_definitive_failure": False,
            "message": "Connection error",
        }
        mock_vandar.return_value = mock_instance

        result = process_withdrawal_requests(withdrawal.id)

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK
        assert withdrawal.track_id == str(withdrawal.id)
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count
        assert "PSP Unconfirmed" in result

    def test_definitive_rejection_refunds_wallet_and_marks_failed(
        self, customer, bank_card, mocker
    ):
        """
        When PSP definitively rejects the request (e.g. invalid IBAN 400),
        the withdrawal must be marked FAILED and the wallet must be refunded.
        """
        withdrawal = self._create_pending_withdrawal(customer, bank_card)
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        mock_instance.create_settlement.return_value = {
            "error": True,
            "is_definitive_failure": True,
            "message": "IBAN is invalid",
        }
        mock_vandar.return_value = mock_instance

        result = process_withdrawal_requests(withdrawal.id)

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.FAILED
        assert withdrawal.errors == "IBAN is invalid"
        # Refund row MUST be created
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count + 1
        refund = Wallet.objects.filter(customer=customer, amount__gt=0).last()
        assert refund.amount == WITHDRAWAL_AMT
        assert "برگشت وجه" in refund.desc
        assert "PSP Definitive Error" in result

    def test_success_marks_sent_to_bank_with_details(
        self, customer, bank_card, mocker
    ):
        """
        When settlement is successfully accepted by PSP, withdrawal is updated with full details.
        """
        withdrawal = self._create_pending_withdrawal(customer, bank_card)
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        mock_instance.create_settlement.return_value = {
            "status": 1,
            "data": {
                "settlement": [
                    {
                        "transaction_id": "TX-987654",
                        "amount": WITHDRAWAL_AMT - 6000,
                        "wage_toman": 6000,
                        "status": "PENDING",
                        "iban": bank_card.Shaba_number,
                        "description": "test settlement",
                        "settlement_date": "1403/02/01",
                        "settlement_time": "10:00",
                        "is_instant": True,
                    }
                ]
            }
        }
        mock_vandar.return_value = mock_instance

        result = process_withdrawal_requests(withdrawal.id)

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK
        assert withdrawal.transaction_id == "TX-987654"
        assert withdrawal.vandar_amount == WITHDRAWAL_AMT - 6000
        assert withdrawal.wage == 6000
        assert withdrawal.bank_send is True
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count
        assert "successfully sent to bank" in result


@pytest.mark.django_db(transaction=True)
class TestInquiryProcessedWithdrawals:

    def test_inquiry_done_completes_withdrawal(self, customer, bank_card, mocker):
        """When inquiry returns DONE, withdrawal is COMPLETED."""
        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.SENT_TO_BANK,
            track_id='track-123',
        )

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.inquiry_settlement.return_value = {
            "status": 1,
            "data": {
                "settlements": [
                    {"status": "DONE"}
                ]
            }
        }
        mock_vandar.return_value = mock_instance

        inquiry_processed_withdrawals()

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.COMPLETED
        assert withdrawal.is_verified is True
        assert withdrawal.confirmed_at is not None

    def test_inquiry_failed_refunds_wallet(self, customer, bank_card, mocker):
        """When inquiry returns FAILED, withdrawal is marked FAILED and wallet is refunded."""
        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.SENT_TO_BANK,
            track_id='track-123',
        )
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.inquiry_settlement.return_value = {
            "status": 1,
            "data": {
                "settlements": [
                    {"status": "FAILED"}
                ]
            }
        }
        mock_vandar.return_value = mock_instance

        inquiry_processed_withdrawals()

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.FAILED
        assert withdrawal.is_verified is False
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count + 1
        refund = Wallet.objects.filter(customer=customer, amount__gt=0).last()
        assert refund.amount == WITHDRAWAL_AMT
