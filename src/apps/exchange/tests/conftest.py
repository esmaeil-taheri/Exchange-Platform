"""
Shared fixtures for apps.exchange tests.
"""

from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.customers.models.bank_card import BankCard
from apps.exchange.models.currency import Currency
from apps.exchange.models.currency_balance import CurrencyBalance
from apps.exchange.models.price_log import CurrencyPriceLog
from apps.exchange.models.daily_transaction_limit import DailyTransactionLimit
from apps.exchange.models.wallet import Wallet
from apps.site_setting.models.setting import SiteSetting
from apps.core.utils.date_time_utils import get_date_time

# ── Constants ─────────────────────────────────────────────────────────────────

PHONE_NUMBER   = '09121234567'
GOLD_PRICE     = 17_500_000        # IRT per gram — round number for easy math
BUY_IRT_AMT    = 1_000_000         # IRT to spend on buy
SELL_XAU_AMT   = Decimal('0.0500') # XAU to sell
IRT_BALANCE    = 5_000_000         # initial IRT wallet balance
XAU_BALANCE    = Decimal('1.0000') # initial XAU wallet balance

# Fixed price-calculation result used in unit tests.
MOCK_PRICE_BUY = {
    'message': 'Success',
    'data': {
        'amount': str(BUY_IRT_AMT),
        'total_amount': 995_000,
        'gold_amount': '0.0560',
        'maintenance_fee': 0,
        'net_amount': 980_000,
        'fee_toman': 15_000,
        'price_per_gram': GOLD_PRICE,
        'discount_amount': 0,
    }
}

MOCK_PRICE_SELL = {
    'message': 'Success',
    'data': {
        'amount': str(SELL_XAU_AMT),
        'total_amount': 862_500,
        'gold_amount': str(SELL_XAU_AMT),
        'maintenance_fee': 0,
        'net_amount': 875_000,
        'fee_toman': 12_500,
        'price_per_gram': GOLD_PRICE,
        'discount_amount': 0,
    }
}


# ── Fixtures: Users & Customers ───────────────────────────────────────────────

@pytest.fixture
def user(db):
    return CustomUser.objects.create(
        username=f'user-{PHONE_NUMBER}',
        phone_number=PHONE_NUMBER,
        last_ip_address='127.0.0.1',
    )


@pytest.fixture
def customer(user):
    return user.customer_profile


@pytest.fixture
def authenticated_customer(customer):
    """Customer with status='authenticated' — required by IsCustomerAuthenticated."""
    customer.status = 'authenticated'
    customer.save(update_fields=['status'])
    return customer


@pytest.fixture
def bank_card(customer, db):
    """Verified bank card — required by gateway buy flow."""
    return BankCard.objects.create(
        customer=customer,
        bank_name='Mellat Bank',
        card_number='6037997123456789',
        is_verified=True,
        is_show=True,
        check_again_on=timezone.now(),
    )


# ── Fixtures: Exchange DB State ───────────────────────────────────────────────

@pytest.fixture
def currency(db):
    """XAU18 currency with buying and selling enabled."""
    return Currency.objects.create(
        symbol='XAU18',
        fa_title='طلا ۱۸ عیار',
        en_title='Gold 18k',
        logo_url='https://example.com/logo.png',
        is_buy=True,
        is_sell=True,
        buy_from_wallet=True,
        buy_from_gateway=True,
        lowest_amount_buy=Decimal('0.0100'),
        lowest_amount_sell=Decimal('0.0100'),
        fixed_buy_fee_toman=5_000,
        buy_fee_percent=Decimal('0.5'),
        fixed_sell_fee_toman=5_000,
        sell_fee_percent=Decimal('0.5'),
        maintenance_fee=Decimal('0'),
    )


@pytest.fixture
def price_log(currency, db):
    """Latest price log for XAU18."""
    return CurrencyPriceLog.objects.create(
        currency=currency,
        price=GOLD_PRICE,
        timestamp=int(timezone.now().timestamp()),
    )


@pytest.fixture
def currency_balance(currency, db):
    """System inventory of XAU18 — large enough for any test purchase."""
    return CurrencyBalance.objects.create(
        currency=currency,
        active_balance=Decimal('1000.0000'),
        locked_balance=Decimal('0.0000'),
    )


@pytest.fixture
def daily_limit(db):
    """Daily transaction limits — set very high so tests are never blocked."""
    return DailyTransactionLimit.objects.create(
        buy_amount=1_000_000_000,
        sell_amount=1_000_000_000,
    )


@pytest.fixture
def site_settings(db):
    """SiteSetting with buy and sell enabled."""
    obj, _ = SiteSetting.objects.get_or_create(pk=1)
    obj.is_buy = True
    obj.is_sell = True
    obj.save()
    return obj


@pytest.fixture
def irt_wallet(customer, db):
    """IRT wallet entry giving the customer IRT_BALANCE."""
    ts = get_date_time()['timestamp']
    return Wallet.objects.create(
        customer=customer,
        wallet_type='irt',
        amount=IRT_BALANCE,
        desc='test deposit',
        ip='127.0.0.1',
        created_at=ts,
        verified_at=ts,
        is_verified=True,
    )


@pytest.fixture
def xau_wallet(customer, db):
    """XAU wallet entry giving the customer XAU_BALANCE grams."""
    ts = get_date_time()['timestamp']
    return Wallet.objects.create(
        customer=customer,
        wallet_type='xau',
        amount=XAU_BALANCE,
        desc='test xau deposit',
        ip='127.0.0.1',
        created_at=ts,
        verified_at=ts,
        is_verified=True,
    )


# ── Fixtures: Mocks ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_site_settings(mocker, site_settings):
    """Patches get_site_settings used inside ExchangeService."""
    return mocker.patch(
        'apps.exchange.services.exchange_services.get_site_settings',
        return_value=site_settings,
    )


@pytest.fixture
def mock_price_buy(mocker):
    """Patches PriceService to return a fixed buy-price dict."""
    return mocker.patch(
        'apps.exchange.services.exchange_services.PriceService.calculate_xau18_currency_price',
        return_value=MOCK_PRICE_BUY,
    )


@pytest.fixture
def mock_price_sell(mocker):
    """Patches PriceService to return a fixed sell-price dict."""
    return mocker.patch(
        'apps.exchange.services.exchange_services.PriceService.calculate_xau18_currency_price',
        return_value=MOCK_PRICE_SELL,
    )


@pytest.fixture
def mock_daily_limit(mocker):
    """Patches DailyLimitService so no DailyTransactionLimit row is needed."""
    return mocker.patch(
        'apps.exchange.services.exchange_services.DailyLimitService.check_daily_limit',
        return_value=None,
    )


@pytest.fixture
def mock_system_balance(mocker):
    """Patches CurrencyBalanceService to report a large available system balance."""
    return mocker.patch(
        'apps.exchange.services.exchange_services.CurrencyBalanceService.calculate_available_balance_for_update',
        return_value=Decimal('500.0000'),
    )


@pytest.fixture
def mock_rate_limit(mocker):
    """Bypasses the rate limiter for API tests."""
    return mocker.patch(
        'apps.core.utils.rate_limiter.limiter.check',
        return_value=(True, {'limit': 100, 'remaining': 99, 'retry_after': 0}),
    )


# ── Fixtures: HTTP Clients ────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def auth_client_authenticated(user, authenticated_customer):
    """Authenticated client whose customer has status='authenticated'."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client
