"""
End-to-end proof that a retried financial request produces one effect.

The bug these cover is not a race. It is the ordinary path: a client posts an
order, the response is lost to a timeout, the worker settles the order, and the
client — seeing nothing — posts again. The pending-transaction guard only holds
while the order is pending, so once it settles the second request sails
straight through and the customer trades twice.

Each test therefore drives that exact sequence: submit, settle, resubmit.
"""

from decimal import Decimal

import pytest
from unittest.mock import MagicMock

from apps.core.exceptions.idempotency_exceptions import IdempotencyKeyConflict
from apps.core.models.idempotency import IdempotencyRecord
from apps.exchange.exceptions.exchange_exceptions import InsufficientUserBalance
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.exchange.services.exchange_services import ExchangeService

from .conftest import BUY_IRT_AMT, MOCK_PRICE_SELL, SELL_XAU_AMT, XAU_BALANCE, IRT_BALANCE

KEY = 'e7c1f0aa-9b3d-4c62-8a11-5d9e2f7b0c34'
OTHER_KEY = '11112222-3333-4444-5555-666677778888'


def _make_request(user):
    req = MagicMock()
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


def _settle_all_pending():
    """Stand in for the settlement worker: move pending orders to success."""
    Transaction.objects.filter(status='pending').update(
        status='success', is_checked=True)


def _xau_balance(user):
    return WalletSelector.get_user_balance_under_customer_lock(
        user_id=user.id, wallet_type='xau')


def _irt_balance(user):
    return WalletSelector.get_user_balance_under_customer_lock(
        user_id=user.id, wallet_type='irt')


# ═════════════════════════════════════════════════════════════════════════════
# Sell — the highest-risk duplicate, because the gold is debited immediately
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSellIdempotency:

    def test_retry_after_settlement_sells_twice_without_a_key(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit,
    ):
        """
        The bug, reproduced.

        This is not an aspiration — it documents what the endpoint still does
        for any client that does not send a key, and is the reason
        IDEMPOTENCY_REQUIRED exists.
        """
        request = _make_request(user)

        ExchangeService.sell_asset(request, 'XAU18', SELL_XAU_AMT, False)
        _settle_all_pending()
        ExchangeService.sell_asset(request, 'XAU18', SELL_XAU_AMT, False)

        assert Transaction.objects.filter(transaction_type='sell').count() == 2
        assert _xau_balance(user) == XAU_BALANCE - (SELL_XAU_AMT * 2)

    def test_retry_after_settlement_sells_once_with_a_key(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit,
    ):
        """The same sequence, with a key: exactly one financial effect."""
        request = _make_request(user)

        first = ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)
        _settle_all_pending()
        second = ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)

        assert Transaction.objects.filter(transaction_type='sell').count() == 1
        assert Wallet.objects.filter(wallet_type='xau', amount__lt=0).count() == 1
        assert _xau_balance(user) == XAU_BALANCE - SELL_XAU_AMT
        assert second == first

    def test_replay_returns_the_original_response_not_a_fresh_quote(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit, mocker,
    ):
        """
        A replay must not re-price the order.

        Pricing on replay would let a retry answer at a price the customer
        never agreed to, and would burn a lock and a price read for nothing.
        """
        request = _make_request(user)
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)
        _settle_all_pending()

        spy = mocker.patch(
            'apps.exchange.services.exchange_services.PriceService.calculate_xau18_currency_price'
        )
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)

        spy.assert_not_called()

    def test_same_key_with_a_different_amount_is_rejected(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit,
    ):
        request = _make_request(user)
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)
        _settle_all_pending()

        with pytest.raises(IdempotencyKeyConflict):
            ExchangeService.sell_asset(
                request, 'XAU18', Decimal('0.9000'), False, idempotency_key=KEY)

        assert Transaction.objects.filter(transaction_type='sell').count() == 1

    def test_a_different_key_is_a_genuinely_new_order(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit,
    ):
        """
        Idempotency must not block a customer who really does want to sell
        again — that is a new intent, and it carries a new key.
        """
        request = _make_request(user)
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)
        _settle_all_pending()
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=OTHER_KEY)

        assert Transaction.objects.filter(transaction_type='sell').count() == 2

    def test_a_rejected_order_does_not_burn_the_key(
        self, user, customer, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit,
    ):
        """
        A request that fails has no effect to protect, so its key must be free.

        This falls out of the claim sharing a transaction with the work: the
        rollback takes the claim with it.
        """
        request = _make_request(user)

        # The shared mock quotes a fixed gold amount, so the oversized order
        # has to be quoted explicitly for the balance check to reject it.
        oversized = {'message': 'Success', 'data': dict(MOCK_PRICE_SELL['data'])}
        oversized['data']['gold_amount'] = '99.0000'
        mock_price_sell.return_value = oversized

        with pytest.raises(InsufficientUserBalance):
            ExchangeService.sell_asset(
                request, 'XAU18', Decimal('99.0000'), False, idempotency_key=KEY)

        assert IdempotencyRecord.objects.count() == 0

        mock_price_sell.return_value = MOCK_PRICE_SELL

        # The same key now works for a real order.
        ExchangeService.sell_asset(
            request, 'XAU18', SELL_XAU_AMT, False, idempotency_key=KEY)
        assert Transaction.objects.filter(transaction_type='sell').count() == 1


# ═════════════════════════════════════════════════════════════════════════════
# Buy from wallet — IRT is debited immediately, same shape as sell
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestWalletBuyIdempotency:

    def test_retry_after_settlement_buys_once_with_a_key(
        self, user, customer, currency, irt_wallet, currency_balance,
        mock_site_settings, mock_price_buy, mock_daily_limit, mock_system_balance,
    ):
        request = _make_request(user)

        first = ExchangeService.buy_asset(
            request, 'XAU18', BUY_IRT_AMT, True, idempotency_key=KEY)
        _settle_all_pending()
        second = ExchangeService.buy_asset(
            request, 'XAU18', BUY_IRT_AMT, True, idempotency_key=KEY)

        assert Transaction.objects.filter(transaction_type='buy').count() == 1
        assert Wallet.objects.filter(wallet_type='irt', amount__lt=0).count() == 1
        assert _irt_balance(user) == IRT_BALANCE - 995_000
        assert second == first

    def test_retry_after_settlement_buys_twice_without_a_key(
        self, user, customer, currency, irt_wallet, currency_balance,
        mock_site_settings, mock_price_buy, mock_daily_limit, mock_system_balance,
    ):
        request = _make_request(user)

        ExchangeService.buy_asset(request, 'XAU18', BUY_IRT_AMT, True)
        _settle_all_pending()
        ExchangeService.buy_asset(request, 'XAU18', BUY_IRT_AMT, True)

        assert Transaction.objects.filter(transaction_type='buy').count() == 2

    def test_wallet_and_gateway_buys_cannot_share_a_key(
        self, user, customer, currency, irt_wallet, bank_card, currency_balance,
        mock_site_settings, mock_price_buy, mock_daily_limit, mock_system_balance,
    ):
        """
        Both branches live behind one endpoint, so the fingerprint — not the
        endpoint name — is what separates them.
        """
        request = _make_request(user)
        ExchangeService.buy_asset(
            request, 'XAU18', BUY_IRT_AMT, True, idempotency_key=KEY)
        _settle_all_pending()

        with pytest.raises(IdempotencyKeyConflict):
            ExchangeService.buy_asset(
                request, 'XAU18', BUY_IRT_AMT, False, idempotency_key=KEY)


# ═════════════════════════════════════════════════════════════════════════════
# HTTP layer — the header actually reaches the service
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIdempotencyOverHttp:

    URL = '/api/v1/exchange/sell/'

    def test_duplicate_post_with_the_same_header_sells_once(
        self, auth_client_authenticated, user, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit, mock_rate_limit,
    ):
        payload = {'aseet': 'XAU18', 'amount': str(SELL_XAU_AMT), 'card_withdaraw': False}

        first = auth_client_authenticated.post(
            self.URL, payload, format='json', HTTP_IDEMPOTENCY_KEY=KEY)
        _settle_all_pending()
        second = auth_client_authenticated.post(
            self.URL, payload, format='json', HTTP_IDEMPOTENCY_KEY=KEY)

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json() == first.json()
        assert Transaction.objects.filter(transaction_type='sell').count() == 1

    def test_reused_header_with_a_different_body_returns_422(
        self, auth_client_authenticated, user, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit, mock_rate_limit,
    ):
        auth_client_authenticated.post(
            self.URL,
            {'aseet': 'XAU18', 'amount': str(SELL_XAU_AMT), 'card_withdaraw': False},
            format='json', HTTP_IDEMPOTENCY_KEY=KEY)
        _settle_all_pending()

        response = auth_client_authenticated.post(
            self.URL,
            {'aseet': 'XAU18', 'amount': '0.9000', 'card_withdaraw': False},
            format='json', HTTP_IDEMPOTENCY_KEY=KEY)

        assert response.status_code == 422
        assert Transaction.objects.filter(transaction_type='sell').count() == 1

    def test_malformed_header_is_rejected_before_any_work(
        self, auth_client_authenticated, user, currency, xau_wallet,
        mock_site_settings, mock_price_sell, mock_daily_limit, mock_rate_limit,
    ):
        response = auth_client_authenticated.post(
            self.URL,
            {'aseet': 'XAU18', 'amount': str(SELL_XAU_AMT), 'card_withdaraw': False},
            format='json', HTTP_IDEMPOTENCY_KEY='nope')

        assert response.status_code == 400
        assert Transaction.objects.count() == 0
