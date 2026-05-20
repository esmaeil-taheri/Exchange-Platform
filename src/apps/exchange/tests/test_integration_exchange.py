"""
Integration Tests — exchange
──────────────────────────────
Full DB state verification for buy and sell flows.
All fixtures are real DB objects; only PriceService and DailyLimitService
are mocked to avoid price-log and limit-table dependencies.
"""

from decimal import Decimal
import pytest
from unittest.mock import MagicMock
from django.db.models import Sum

from apps.exchange.services.exchange_services import ExchangeService
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet

from .conftest import IRT_BALANCE, XAU_BALANCE, MOCK_PRICE_BUY, MOCK_PRICE_SELL


def _make_request(user):
    req = MagicMock()
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


# ═════════════════════════════════════════════════════════════════════════════
# buy_from_wallet
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestBuyFromWalletIntegration:

    def test_buy_creates_irt_debit_and_pending_transaction(
        self, user, customer, irt_wallet, currency, currency_balance,
        mock_site_settings, mock_price_buy, mock_daily_limit
    ):
        """
        After a successful buy from wallet:
          - One pending Transaction must be persisted.
          - A negative IRT wallet entry equal to total_amount must exist.
          - The net IRT balance must equal IRT_BALANCE - total_amount.
        """
        total_amount = MOCK_PRICE_BUY['data']['total_amount']

        ExchangeService.buy_asset(
            request=_make_request(user),
            asset='XAU18',
            amount=1_000_000,
            buy_from_wallet=True,
        )

        # Transaction created and pending
        txn = Transaction.objects.filter(
            customer=customer, transaction_type='buy'
        ).first()
        assert txn is not None
        assert txn.status == 'pending'
        assert txn.deposit_method == 'wallet'

        # IRT debit persisted
        debit = Wallet.objects.filter(
            customer=customer, wallet_type='irt', amount__lt=0
        ).first()
        assert debit is not None
        assert int(debit.amount) == -total_amount

        # Net balance correctly reduced
        net = Wallet.objects.filter(
            customer=customer, wallet_type='irt', is_verified=True
        ).aggregate(total=Sum('amount'))['total']
        assert int(net) == IRT_BALANCE - total_amount


# ═════════════════════════════════════════════════════════════════════════════
# sell_to_wallet
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestSellToWalletIntegration:

    def test_sell_creates_xau_debit_and_pending_transaction(
        self, user, customer, xau_wallet, currency,
        mock_site_settings, mock_price_sell, mock_daily_limit
    ):
        """
        After a successful sell to wallet:
          - One pending Transaction of type 'sell' must be persisted.
          - A negative XAU wallet entry must exist.
          - The net XAU balance must be reduced by gold_amount.
        """
        gold_amount = Decimal(MOCK_PRICE_SELL['data']['gold_amount'])

        ExchangeService.sell_asset(
            request=_make_request(user),
            asset='XAU18',
            amount=Decimal('0.0500'),
            card_withdaraw=False,
        )

        # Transaction created and pending
        txn = Transaction.objects.filter(
            customer=customer, transaction_type='sell'
        ).first()
        assert txn is not None
        assert txn.status == 'pending'

        # XAU debit persisted
        debit = Wallet.objects.filter(
            customer=customer, wallet_type='xau', amount__lt=0
        ).first()
        assert debit is not None
        assert abs(debit.amount) == gold_amount

        # Net XAU balance correctly reduced
        net = Wallet.objects.filter(
            customer=customer, wallet_type='xau', is_verified=True
        ).aggregate(total=Sum('amount'))['total']
        assert net == XAU_BALANCE - gold_amount
