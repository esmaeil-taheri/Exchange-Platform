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
    UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES,
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

    def test_already_processing_or_claimed_is_skipped(
        self, customer, bank_card, mocker
    ):
        """
        TASK 1.2:
        If a withdrawal is already in PROCESSING status (e.g. claimed by another worker),
        a concurrent worker must exit immediately without calling Vandar.
        """
        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.PROCESSING,
            track_id='claimed-track',
        )

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_vandar.return_value = mock_instance

        result = process_withdrawal_requests(withdrawal.id)

        # Vandar create_settlement must NEVER be called
        mock_instance.create_settlement.assert_not_called()
        assert "already processed or currently claimed" in result or "already has track_id" in result

    def test_claim_phase_sets_processing_before_external_call(
        self, customer, bank_card, mocker
    ):
        """
        TASK 1.2:
        Verifies that status is atomically set to PROCESSING before Vandar create_settlement runs.
        """
        withdrawal = self._create_pending_withdrawal(customer, bank_card)

        observed_status = []

        def side_effect_inspect_status(*args, **kwargs):
            # Inspect the DB row while create_settlement is running
            w = Withdrawal.objects.get(id=withdrawal.id)
            observed_status.append(w.status)
            return {
                "status": 1,
                "data": {
                    "settlement": [
                        {
                            "transaction_id": "TX-111",
                            "amount": WITHDRAWAL_AMT - 6000,
                            "wage_toman": 6000,
                            "status": "PENDING",
                            "iban": bank_card.Shaba_number,
                            "description": "test",
                            "settlement_date": "1403/02/01",
                            "settlement_time": "10:00",
                            "is_instant": True,
                        }
                    ]
                }
            }

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        mock_instance.create_settlement.side_effect = side_effect_inspect_status
        mock_vandar.return_value = mock_instance

        process_withdrawal_requests(withdrawal.id)

        # While Vandar was being called, status in DB MUST HAVE BEEN 'processing'
        assert observed_status == [Withdrawal.WithdrawalStatus.PROCESSING]

        # After completion, status is 'sent_to_bank'
        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK

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

    def test_multiple_withdrawals_without_transaction_id_store_none_without_unique_collision(
        self, customer, bank_card, mocker
    ):
        """
        Verifies that when PSP response lacks transaction_id (None or missing),
        the field is stored as None (SQL NULL) instead of empty string "",
        allowing multiple withdrawals without violating unique constraint.
        """
        w1 = self._create_pending_withdrawal(customer, bank_card)
        w2 = self._create_pending_withdrawal(customer, bank_card)

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.wage = 6000
        # No transaction_id in response
        mock_instance.create_settlement.return_value = {
            "status": 1,
            "data": {
                "settlement": [
                    {
                        "amount": WITHDRAWAL_AMT - 6000,
                        "status": "PENDING",
                    }
                ]
            }
        }
        mock_vandar.return_value = mock_instance

        # Process first withdrawal
        process_withdrawal_requests(w1.id)
        # Process second withdrawal (would crash with IntegrityError if "" was stored)
        process_withdrawal_requests(w2.id)

        w1.refresh_from_db()
        w2.refresh_from_db()

        assert w1.transaction_id is None
        assert w2.transaction_id is None
        assert w1.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK
        assert w2.status == Withdrawal.WithdrawalStatus.SENT_TO_BANK


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

    def test_inquiry_recovers_stale_processing_row_when_psp_returns_404(
        self, customer, bank_card, mocker
    ):
        """
        A withdrawal stuck in PROCESSING for longer than
        UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES, whose track_id the PSP reports
        as 404, never reached the gateway: mark it FAILED and refund.
        """
        from datetime import timedelta
        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.PROCESSING,
            track_id='track-999',
        )
        # Comfortably past the refund threshold
        Withdrawal.objects.filter(id=withdrawal.id).update(
            created_at=timezone.now()
            - timedelta(minutes=UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES + 60)
        )
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.inquiry_settlement.return_value = {
            "error": True,
            "is_not_found": True,
            "status_code": 404,
            "message": "HTTP 404",
        }
        mock_vandar.return_value = mock_instance

        inquiry_processed_withdrawals()

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.FAILED
        assert withdrawal.is_verified is False
        assert "PSP track_id not found" in withdrawal.errors
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count + 1
        refund = Wallet.objects.filter(customer=customer, amount__gt=0).last()
        assert refund.amount == WITHDRAWAL_AMT

    def test_young_404_row_is_not_refunded_yet(
        self, customer, bank_card, mocker
    ):
        """
        A 404 alone must not trigger a refund. A settlement submitted moments ago
        can legitimately be unqueryable while Paya batches it; refunding then,
        while the transfer still completes, pays the customer twice. Below the
        threshold the row is left alone for a later run to resolve.
        """
        from datetime import timedelta

        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.PROCESSING,
            track_id='track-fresh',
        )
        Withdrawal.objects.filter(id=withdrawal.id).update(
            created_at=timezone.now()
            - timedelta(minutes=UNCONFIRMED_SETTLEMENT_REFUND_AGE_MINUTES - 10)
        )
        initial_wallets_count = Wallet.objects.filter(customer=customer).count()

        mock_vandar = mocker.patch('apps.settlements.tasks.settlement_tasks.VandarClient')
        mock_instance = MagicMock()
        mock_instance.inquiry_settlement.return_value = {
            "error": True,
            "is_not_found": True,
            "status_code": 404,
            "message": "HTTP 404",
        }
        mock_vandar.return_value = mock_instance

        inquiry_processed_withdrawals()

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.PROCESSING
        assert Wallet.objects.filter(customer=customer).count() == initial_wallets_count

    def test_stuck_withdrawals_ignores_processing_rows(
        self, customer, bank_card, mocker
    ):
        """
        A PROCESSING row always carries a track_id (both are written in the same
        save), so it may already be at the PSP. The stuck-withdrawal net must
        never resubmit it — that is inquiry_processed_withdrawals' job.
        """
        from datetime import timedelta
        from apps.settlements.tasks.settlement_tasks import process_stuck_withdrawals

        withdrawal = Withdrawal.objects.create(
            customer=customer,
            card=bank_card,
            amount=WITHDRAWAL_AMT,
            settlement_method='پایا',
            status=Withdrawal.WithdrawalStatus.PROCESSING,
            track_id='track-inflight',
        )
        Withdrawal.objects.filter(id=withdrawal.id).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        mock_delay = mocker.patch(
            'apps.settlements.tasks.settlement_tasks.process_withdrawal_requests.delay'
        )

        process_stuck_withdrawals()

        withdrawal.refresh_from_db()
        assert withdrawal.status == Withdrawal.WithdrawalStatus.PROCESSING
        mock_delay.assert_not_called()
