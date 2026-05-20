"""
Unit Tests — PriceService
───────────────────────────
Tests calculate_xau18_currency_price for both buy and sell paths.
Requires a real Currency + CurrencyPriceLog in the DB.
"""

from decimal import Decimal
import pytest

from apps.exchange.services.price_services import PriceService
from apps.exchange.exceptions.price_exceptions import InsufficientBuyAmount, InsufficientSellAmount

from .conftest import GOLD_PRICE


# ═════════════════════════════════════════════════════════════════════════════
# calculate_xau18_currency_price
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCalculateXau18CurrencyPrice:

    def test_buy_irt_returns_correct_structure(self, currency, price_log):
        """A valid IRT buy amount must return a dict with all expected keys."""
        result = PriceService.calculate_xau18_currency_price(
            unit='IRT',
            amount=1_000_000,
            transaction_type='buy'
        )
        assert result['message'] == 'Success'
        data = result['data']
        assert 'gold_amount' in data
        assert 'total_amount' in data
        assert 'fee_toman' in data
        assert 'price_per_gram' in data
        assert Decimal(data['gold_amount']) > 0
        assert data['price_per_gram'] == GOLD_PRICE

    def test_sell_xau_returns_correct_structure(self, currency, price_log):
        """A valid XAU sell amount must return a dict with all expected keys."""
        result = PriceService.calculate_xau18_currency_price(
            unit='XAU18',
            amount=Decimal('0.0500'),
            transaction_type='sell'
        )
        assert result['message'] == 'Success'
        data = result['data']
        assert 'total_amount' in data
        assert 'gold_amount' in data
        assert data['total_amount'] > 0

    def test_buy_total_does_not_exceed_input_amount(self, currency, price_log):
        """
        The iterative fee loop in calculate_xau18_currency_price must ensure
        total_amount <= requested IRT amount.
        """
        amount = 500_000
        result = PriceService.calculate_xau18_currency_price(
            unit='IRT', amount=amount, transaction_type='buy'
        )
        assert result['data']['total_amount'] <= amount

    def test_buy_below_minimum_raises_insufficient_buy_amount(self, currency, price_log):
        """Amounts that yield gold_amount < lowest_amount_buy must raise InsufficientBuyAmount."""
        with pytest.raises(InsufficientBuyAmount):
            # 100 IRT / 17,500,000 per gram ≈ 0.000006g — well below 0.01g minimum
            PriceService.calculate_xau18_currency_price(
                unit='IRT', amount=100, transaction_type='buy'
            )

    def test_sell_below_minimum_raises_insufficient_sell_amount(self, currency, price_log):
        """Gold amounts below lowest_amount_sell must raise InsufficientSellAmount."""
        with pytest.raises(InsufficientSellAmount):
            PriceService.calculate_xau18_currency_price(
                unit='XAU18', amount=Decimal('0.0001'), transaction_type='sell'
            )
