"""
Unit Tests — ExchangeService
──────────────────────────────
Tests buy_asset and sell_asset branch logic.
PriceService, DailyLimitService, and system-balance checks are mocked.
Currency is created in the DB (simple fixture with no external dependencies).
"""

from decimal import Decimal
import pytest
from unittest.mock import MagicMock

from apps.exchange.services.exchange_services import ExchangeService
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.exchange.exceptions.currency_exceptions import CurrencyNotBuyable
from apps.exchange.exceptions.exchange_exceptions import (
    InsufficientSystemBalance, InsufficientUserBalance,
)
from apps.customers.exceptions.customer_exceptions import CustomerSuspended
from apps.core.exceptions.base import ActionDisabled

from .conftest import IRT_BALANCE, XAU_BALANCE, MOCK_PRICE_BUY, MOCK_PRICE_SELL


def _make_request(user):
    req = MagicMock()
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


# ═════════════════════════════════════════════════════════════════════════════
# buy_asset
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestBuyAsset:

    def test_buy_globally_disabled_raises_currency_not_buyable(
        self, user, mock_site_settings, site_settings, currency
    ):
        """When site_settings.is_buy is False, CurrencyNotBuyable must be raised."""
        site_settings.is_buy = False
        site_settings.save()

        with pytest.raises(CurrencyNotBuyable):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_buy_currency_disabled_raises_currency_not_buyable(
        self, user, mock_site_settings, currency
    ):
        """When currency.is_buy is False, CurrencyNotBuyable must be raised."""
        currency.is_buy = False
        currency.save(update_fields=['is_buy'])

        with pytest.raises(CurrencyNotBuyable):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_customer_suspended_raises_customer_suspended(
        self, user, customer, mock_site_settings, mock_price_buy, currency
    ):
        """A suspended customer must raise CustomerSuspended before any balance check."""
        customer.status = 'suspended'
        customer.save(update_fields=['status'])

        with pytest.raises(CustomerSuspended):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_pending_transaction_raises_action_disabled(
        self, user, customer, mock_site_settings, mock_price_buy,
        mock_daily_limit, currency
    ):
        """Existing pending transaction for the same currency must raise ActionDisabled."""
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
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_insufficient_system_balance_raises_error(
        self, user, customer, mock_site_settings, mock_price_buy,
        mock_daily_limit, mocker, currency
    ):
        """When available system gold < required gold amount, InsufficientSystemBalance is raised."""
        mocker.patch(
            'apps.exchange.services.exchange_services.CurrencyBalanceService.calculate_available_balance_for_update',
            return_value=Decimal('0.0001'),  # far below requested 0.0560g
        )

        with pytest.raises(InsufficientSystemBalance):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_insufficient_user_balance_raises_error(
        self, user, customer, mock_site_settings, mock_price_buy,
        mock_daily_limit, mock_system_balance, currency
    ):
        """Zero IRT wallet balance must raise InsufficientUserBalance."""
        # No irt_wallet fixture → balance = 0
        with pytest.raises(InsufficientUserBalance):
            ExchangeService.buy_asset(
                request=_make_request(user),
                asset='XAU18', amount=1_000_000, buy_from_wallet=True
            )

    def test_success_buy_from_wallet_returns_message(
        self, user, customer, irt_wallet, mock_site_settings, mock_price_buy,
        mock_daily_limit, mock_system_balance, currency
    ):
        """A successful wallet buy must return a dict with a 'message' key."""
        result = ExchangeService.buy_asset(
            request=_make_request(user),
            asset='XAU18', amount=1_000_000, buy_from_wallet=True
        )
        assert 'message' in result


# ═════════════════════════════════════════════════════════════════════════════
# sell_asset
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
class TestSellAsset:

    def test_sell_globally_disabled_raises_currency_not_buyable(
        self, user, mock_site_settings, site_settings, currency
    ):
        """When site_settings.is_sell is False, CurrencyNotBuyable must be raised."""
        site_settings.is_sell = False
        site_settings.save()

        with pytest.raises(CurrencyNotBuyable):
            ExchangeService.sell_asset(
                request=_make_request(user),
                asset='XAU18', amount=Decimal('0.0500'), card_withdaraw=False
            )

    def test_insufficient_xau_balance_raises_error(
        self, user, customer, mock_site_settings, mock_price_sell,
        mock_daily_limit, currency
    ):
        """Zero XAU wallet balance must raise InsufficientUserBalance."""
        with pytest.raises(InsufficientUserBalance):
            ExchangeService.sell_asset(
                request=_make_request(user),
                asset='XAU18', amount=Decimal('0.0500'), card_withdaraw=False
            )

    def test_success_sell_to_wallet_returns_message(
        self, user, customer, xau_wallet, mock_site_settings, mock_price_sell,
        mock_daily_limit, currency
    ):
        """A successful wallet sell must return a dict with a 'message' key."""
        result = ExchangeService.sell_asset(
            request=_make_request(user),
            asset='XAU18', amount=Decimal('0.0500'), card_withdaraw=False
        )
        assert 'message' in result
