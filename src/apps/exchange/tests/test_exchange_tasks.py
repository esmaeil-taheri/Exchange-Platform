from decimal import Decimal
import pytest

from apps.core.utils.date_time_utils import get_date_time
from apps.exchange.models.price_log import CurrencyPriceLog
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.wallet import Wallet
from apps.exchange.services.price_services import PriceService
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.exchange.tasks.exchange_tasks import (
    process_buy_transactions,
    process_sell_transactions,
)
from apps.payments.models.invoice import Invoice
from apps.settlements.models.withdrawal import Withdrawal


@pytest.mark.django_db
class TestProcessBuyTransactions:

    def test_process_buy_from_wallet_success(self, customer, currency, price_log, irt_wallet):
        now_ts = get_date_time()["timestamp"] - 10
        gold_amount = Decimal("0.0500")
        unit_price = price_log.price

        calc = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=gold_amount,
            unit_price_irt=unit_price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=-calc["total"],
            desc="خرید طلا",
            created_at=now_ts,
            verified_at=now_ts,
            ip="127.0.0.1",
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=gold_amount,
            fee_irt=calc["fee"],
            unit_price_irt=unit_price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],  # buy
            status=Transaction.TRANSACTIONSTATUSES[0][0],        # pending
            deposit_method=Transaction.DEPOSITTYPES[0][0],       # wallet
            created_at=now_ts,
        )

        process_buy_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[1][0]  # success
        assert trans.is_checked is True
        assert trans.processed_at is not None

        xau_balance = WalletSelector.get_user_balance_under_customer_lock(
            user_id=customer.user.id,
            wallet_type=Wallet.WALLETTYPES[1][0],
        )
        assert xau_balance == gold_amount

    def test_process_buy_from_gateway_success(self, customer, currency, price_log):
        now_ts = get_date_time()["timestamp"] - 10
        gold_amount = Decimal("0.0500")
        unit_price = price_log.price

        calc = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=gold_amount,
            unit_price_irt=unit_price,
            currency=currency,
        )

        invoice = Invoice.objects.create(
            customer=customer,
            total_price=calc["total"],
            unit_price=unit_price,
            fee=calc["fee"],
            maintenance_fee=calc["maintenance"],
            status=Invoice.STATUS_CHOICES[1][0],  # paid
            is_paid=True,
            is_processed=True,
            invoice_type=Invoice.INVOICE_TYPES[1][0],  # buy
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            invoice=invoice,
            amount=gold_amount,
            fee_irt=calc["fee"],
            unit_price_irt=unit_price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],  # buy
            status=Transaction.TRANSACTIONSTATUSES[0][0],        # pending
            deposit_method=Transaction.DEPOSITTYPES[1][0],       # gateway
            created_at=now_ts,
        )

        process_buy_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[1][0]
        assert trans.is_checked is True

        xau_balance = WalletSelector.get_user_balance_under_customer_lock(
            user_id=customer.user.id,
            wallet_type=Wallet.WALLETTYPES[1][0],
        )
        assert xau_balance == gold_amount

    def test_process_buy_negative_irt_balance_rejects_without_refund(self, customer, currency, price_log):
        now_ts = get_date_time()["timestamp"] - 10
        # Negative balance entry
        Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=-10_000_000,
            desc="negative",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        calc = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=Decimal("0.0500"),
            unit_price_irt=price_log.price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=-calc["total"],
            desc="خرید",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=Decimal("0.0500"),
            fee_irt=calc["fee"],
            unit_price_irt=price_log.price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            deposit_method=Transaction.DEPOSITTYPES[0][0],
            created_at=now_ts,
        )

        process_buy_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[2][0]  # rejected
        assert trans.reject_reason == "Negative IRT balance"
        assert trans.processed_at is not None

    def test_process_buy_price_mismatch_rejects_and_refunds(self, customer, currency, price_log, irt_wallet):
        now_ts = get_date_time()["timestamp"] - 10
        gold_amount = Decimal("0.0500")

        calc = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=gold_amount,
            unit_price_irt=price_log.price,
            currency=currency,
        )

        fake_total = calc["total"] + 5000  # Price mismatch

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=-fake_total,
            desc="خرید",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=gold_amount,
            fee_irt=calc["fee"],
            unit_price_irt=price_log.price,
            total_price_irt=fake_total,
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            deposit_method=Transaction.DEPOSITTYPES[0][0],
            created_at=now_ts,
        )

        process_buy_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[2][0]
        assert trans.reject_reason == "Transaction total price is not match"
        assert trans.processed_at is not None

        # Verify refund entry exists
        refund_wallet = Wallet.objects.filter(
            customer=customer,
            amount=fake_total,
            desc__contains="برگشت خرید ناموفق",
        ).first()
        assert refund_wallet is not None

    def test_process_buy_market_price_deviation_rejects_and_refunds(self, customer, currency, price_log, irt_wallet):
        now_ts = get_date_time()["timestamp"] - 10
        order_unit_price = 10_000_000

        # Market price increases by > 1%
        price_log.price = 10_200_000
        price_log.save()

        calc = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=Decimal("0.0500"),
            unit_price_irt=order_unit_price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[0][0],
            amount=-calc["total"],
            desc="خرید",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=Decimal("0.0500"),
            fee_irt=calc["fee"],
            unit_price_irt=order_unit_price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[0][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            deposit_method=Transaction.DEPOSITTYPES[0][0],
            created_at=now_ts,
        )

        process_buy_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[2][0]
        assert trans.reject_reason == "Transaction unit price is not match with last price"
        assert trans.processed_at is not None


@pytest.mark.django_db
class TestProcessSellTransactions:

    def test_process_sell_to_wallet_success_with_fractional_price(self, customer, currency, xau_wallet):
        """Tests sell settlement with a realistic non-round market price to verify C-01 fix."""
        market_price = 7_332_911
        gold_amount = Decimal("0.0507")
        now_ts = get_date_time()["timestamp"] - 10

        price_log = CurrencyPriceLog.objects.create(
            currency=currency,
            price=market_price,
            timestamp=now_ts,
        )

        calc = PriceService.calculate_sell_total_from_snapshot(
            gold_amount=gold_amount,
            unit_price_irt=market_price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],  # xau
            amount=-gold_amount,
            desc="فروش طلا",
            created_at=now_ts,
            verified_at=now_ts,
            ip="127.0.0.1",
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=gold_amount,
            fee_irt=calc["fee"],
            unit_price_irt=market_price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[1][0],  # sell
            status=Transaction.TRANSACTIONSTATUSES[0][0],        # pending
            withdraw_method=Transaction.WITHDRAWTYPES[0][0],     # wallet
            created_at=now_ts,
        )

        process_sell_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[1][0]  # success
        assert trans.is_checked is True
        assert trans.processed_at is not None

        irt_balance = WalletSelector.get_user_balance_under_customer_lock(
            user_id=customer.user.id,
            wallet_type=Wallet.WALLETTYPES[0][0],
        )
        assert irt_balance == calc["total"]

    def test_process_sell_to_bank_creates_withdrawal(self, customer, currency, price_log, xau_wallet, bank_card, mocker):
        now_ts = get_date_time()["timestamp"] - 10
        gold_amount = Decimal("0.0500")

        mock_apply_async = mocker.patch(
            "apps.exchange.tasks.exchange_tasks.process_withdrawal_requests.apply_async"
        )

        calc = PriceService.calculate_sell_total_from_snapshot(
            gold_amount=gold_amount,
            unit_price_irt=price_log.price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],
            amount=-gold_amount,
            desc="فروش طلا",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            card=bank_card,
            amount=gold_amount,
            fee_irt=calc["fee"],
            unit_price_irt=price_log.price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[1][0],  # sell
            status=Transaction.TRANSACTIONSTATUSES[0][0],        # pending
            withdraw_method=Transaction.WITHDRAWTYPES[1][0],     # bank
            created_at=now_ts,
        )

        process_sell_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[1][0]
        assert trans.is_checked is True
        assert trans.processed_at is not None

        withdrawal = Withdrawal.objects.filter(customer=customer).first()
        assert withdrawal is not None
        assert withdrawal.amount == calc["total"]
        assert withdrawal.card == bank_card
        assert withdrawal.status == Withdrawal.WithdrawalStatus.PENDING
        mock_apply_async.assert_called_once_with(args=[withdrawal.id], countdown=10)

    def test_process_sell_negative_xau_balance_rejects(self, customer, currency, price_log):
        now_ts = get_date_time()["timestamp"] - 10
        Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],
            amount=-Decimal("5.0000"),
            desc="negative xau",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        calc = PriceService.calculate_sell_total_from_snapshot(
            gold_amount=Decimal("0.0500"),
            unit_price_irt=price_log.price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],
            amount=-Decimal("0.0500"),
            desc="فروش",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=Decimal("0.0500"),
            fee_irt=calc["fee"],
            unit_price_irt=price_log.price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[1][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            withdraw_method=Transaction.WITHDRAWTYPES[0][0],
            created_at=now_ts,
        )

        process_sell_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[2][0]
        assert trans.reject_reason == "Negative XAU balance"
        assert trans.processed_at is not None

    def test_process_sell_market_deviation_rejects_and_refunds_xau(self, customer, currency, price_log, xau_wallet):
        now_ts = get_date_time()["timestamp"] - 10
        order_unit_price = 10_000_000

        # Market price drops > 1% below order unit price
        price_log.price = 9_800_000
        price_log.save()

        calc = PriceService.calculate_sell_total_from_snapshot(
            gold_amount=Decimal("0.0500"),
            unit_price_irt=order_unit_price,
            currency=currency,
        )

        wallet_debit = Wallet.objects.create(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],
            amount=-Decimal("0.0500"),
            desc="فروش",
            created_at=now_ts,
            verified_at=now_ts,
            is_verified=True,
        )

        trans = Transaction.objects.create(
            customer=customer,
            currency=currency,
            wallet=wallet_debit,
            amount=Decimal("0.0500"),
            fee_irt=calc["fee"],
            unit_price_irt=order_unit_price,
            total_price_irt=calc["total"],
            transaction_type=Transaction.TRANSACTIONTYPES[1][0],
            status=Transaction.TRANSACTIONSTATUSES[0][0],
            withdraw_method=Transaction.WITHDRAWTYPES[0][0],
            created_at=now_ts,
        )

        process_sell_transactions()

        trans.refresh_from_db()
        assert trans.status == Transaction.TRANSACTIONSTATUSES[2][0]
        assert trans.reject_reason == "Transaction unit price is not match with last price"
        assert trans.processed_at is not None

        # Verify XAU refund
        refund_wallet = Wallet.objects.filter(
            customer=customer,
            wallet_type=Wallet.WALLETTYPES[1][0],
            amount=Decimal("0.0500"),
            desc__contains="برگشت فروش ناموفق",
        ).first()
        assert refund_wallet is not None
