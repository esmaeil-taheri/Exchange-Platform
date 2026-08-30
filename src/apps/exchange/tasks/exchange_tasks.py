import logging

from celery import shared_task
from django.db import transaction
from django.dispatch import Signal

from apps.exchange.models.price_log import CurrencyPriceLog
from apps.exchange.models.transaction import Transaction
from apps.core.utils.date_time_utils import get_date_time

from apps.exchange.models.wallet import Wallet
from apps.exchange.selectors.wallet_selectors import WalletSelector
from apps.exchange.services.price_services import PriceService
from apps.settlements.services.settlement_services import SettlementService
from apps.settlements.tasks.settlement_tasks import process_withdrawal_requests

logger = logging.getLogger(__name__)

transaction_processed = Signal()


@shared_task()
def process_buy_transactions():

    """
    Process pending buy transactions in a concurrency-safe and atomic manner.

    This task scans a limited batch of pending buy transactions and attempts to
    settle each one independently. For every transaction, a database row-level
    lock is acquired using `select_for_update(skip_locked=True)` inside a single
    atomic block. This ensures that in a multi-worker environment, each pending
    transaction is claimed and processed by at most one worker, preventing
    double-settlement and duplicate wallet credits.

    Processing flow for each transaction:
        1. Read a batch of pending buy transactions ordered by creation time.
        2. For each transaction, open a database transaction.
        3. Re-fetch and claim the transaction row with
           `select_for_update(skip_locked=True)` while ensuring its status is
           still `pending`.
        4. If the row is already locked or processed by another worker, skip it.
        5. Validate all business rules inside the same atomic block, including:
           - customer IRT balance state
           - total price consistency
           - wallet debit consistency
           - unit price tolerance against latest market price
        6. If validation fails, mark the transaction as rejected and create a
           refund wallet entry when needed.
        7. If validation succeeds, mark the transaction as successful and create
           the purchased asset wallet entry.
        8. Emit the `transaction_processed` signal only after successful commit
           using `transaction.on_commit(...)`.

    Concurrency and safety guarantees:
        - Prevents multiple workers from processing the same transaction.
        - Ensures transaction status update and wallet settlement happen
          atomically.
        - Avoids inconsistent state if a worker crashes before commit; in that
          case, the transaction remains `pending` and can be retried safely.
        - Uses database locking as the source of truth instead of in-memory task
          coordination.

    Notes:
        - This task is intended to behave like a DB-backed work queue.
        - Refunds and successful settlements are recorded as wallet ledger
          entries to preserve auditability.
        - Side effects such as signals are deferred until commit to avoid false
          notifications on rollback.
    """

    now_ts = get_date_time()['timestamp']

    pendings = Transaction.objects.filter(
        status=Transaction.TRANSACTIONSTATUSES[0][0],
        transaction_type=Transaction.TRANSACTIONTYPES[0][0],
        is_checked=False,
        created_at__lt=now_ts
    ).order_by('created_at')[:3]

    logger.info(f"[task=process_buy] Batch started | pending_count={pendings.count()}")

    for trans in pendings:

        currency = trans.currency

        transaction_total_price = PriceService.calculate_buy_total_from_snapshot(
            gold_amount=trans.amount,
            unit_price_irt=trans.unit_price_irt,
            currency=currency
        )

        with transaction.atomic():

            trans = Transaction.objects.select_for_update(skip_locked=True).filter(
                id=trans.id,
                status='pending'
            ).first()

            if trans is None:
                continue

            if trans.deposit_method == Transaction.DEPOSITTYPES[0][0]:
                wallet = trans.wallet
                wallet_amount = abs(wallet.amount)
            if trans.deposit_method == Transaction.DEPOSITTYPES[1][0]:
                invoice = trans.invoice
                wallet_amount = invoice.total_price

            customer = trans.customer
            last_price = CurrencyPriceLog.objects.filter(currency=currency).last()

            if last_price is None:
                logger.error(
                    f"[task=process_buy] No price log found — skipping | "
                    f"transaction_id={trans.id} currency={currency.symbol}"
                )
                continue

            customer_irt_balance = WalletSelector.get_user_balance_for_update(
                user_id=customer.user.id,
                wallet_type=Wallet.WALLETTYPES[0][0]
            )
            if customer_irt_balance < 0:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Negative IRT balance"
                trans.processed_at = now_ts
                trans.save()
                logger.warning(
                    f"[task=process_buy] Transaction REJECTED — negative IRT balance | "
                    f"transaction_id={trans.id} customer_id={customer.id}"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if transaction_total_price['total'] != trans.total_price_irt:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction total price is not match"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[0][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت خرید ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_buy] Transaction REJECTED — price mismatch | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"expected={transaction_total_price['total']} got={trans.total_price_irt} "
                    f"refund={wallet_amount}IRT"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if trans.total_price_irt != wallet_amount:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction total price and wallet amount are not match"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[0][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت خرید ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_buy] Transaction REJECTED — wallet/price mismatch | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"total_price={trans.total_price_irt} wallet_amount={wallet_amount} "
                    f"refund={wallet_amount}IRT"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if trans.unit_price_irt < last_price.price and abs(last_price.price - trans.unit_price_irt) > (trans.unit_price_irt / 100):
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction unit price is not match with last price"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[0][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت خرید ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_buy] Transaction REJECTED — unit price deviation >1% | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"order_price={trans.unit_price_irt} market_price={last_price.price} "
                    f"refund={wallet_amount}IRT"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            trans.is_checked = True
            trans.status = Transaction.TRANSACTIONSTATUSES[1][0]
            trans.processed_at = now_ts
            trans.save()

            Wallet.objects.create(
                customer=customer,
                wallet_type=Wallet.WALLETTYPES[1][0],
                amount=trans.amount,
                desc=f'خرید {currency.fa_title} به شماره فاکتور : {trans.id}',
                created_at=now_ts,
                verified_at=now_ts,
                ip="1.1.1.1",
                is_verified=True
            )

            logger.info(
                f"[task=process_buy] Transaction SUCCESS — XAU credited | "
                f"transaction_id={trans.id} customer_id={customer.id} "
                f"gold={trans.amount}g total={trans.total_price_irt}IRT"
            )

            transaction.on_commit(lambda: transaction_processed.send(
                sender='exchange', transaction_id=trans.id, status=trans.status)
            )

            continue


@shared_task()
def process_sell_transactions():

    """
    Process pending sell transactions in a concurrency-safe and atomic manner.

    This task settles pending sell transactions by claiming each transaction with
    a row-level lock inside a single atomic database transaction. The lock is
    acquired using `select_for_update(skip_locked=True)` so that multiple workers
    can run in parallel without processing the same transaction more than once.

    Processing flow for each transaction:
        1. Read a batch of pending sell transactions ordered by creation time.
        2. For each transaction, start an atomic database transaction.
        3. Re-fetch and claim the transaction row with
           `select_for_update(skip_locked=True)` only if it is still `pending`.
        4. If another worker already claimed the transaction, skip it.
        5. Perform all validations and settlement logic while holding the lock,
           including balance checks, pricing checks, and wallet consistency
           verification.
        6. If validation fails, mark the transaction as rejected and create any
           required compensating wallet entry or refund entry.
        7. If validation succeeds, mark the transaction as successful and create
           the corresponding IRT settlement wallet entry.
        8. Emit the `transaction_processed` signal only after the database
           transaction is successfully committed.

    Concurrency and safety guarantees:
        - Prevents double-settlement in concurrent worker execution.
        - Ensures ledger changes and transaction status updates are committed
          together atomically.
        - If a worker crashes before commit, no partial settlement is persisted,
          and the transaction can be safely retried by another worker.
        - Preserves wallet ledger integrity by recording all financial outcomes
          as explicit wallet entries.

    Notes:
        - This task relies on the database as the coordination mechanism between
          workers.
        - The implementation follows the pattern:
          LOCK -> VALIDATE -> SETTLE -> COMMIT
        - External side effects must be triggered only through
          `transaction.on_commit(...)` to avoid emitting events for rolled-back
          operations.
    """

    now_ts = get_date_time()['timestamp']

    pendings = Transaction.objects.filter(
        status=Transaction.TRANSACTIONSTATUSES[0][0],
        transaction_type=Transaction.TRANSACTIONTYPES[1][0],
        is_checked=False,
        created_at__lt=now_ts
    ).order_by('created_at')[:3]

    logger.info(f"[task=process_sell] Batch started | pending_count={pendings.count()}")

    for trans in pendings:

        currency = trans.currency

        transaction_total_price = PriceService.calculate_sell_total_from_snapshot(
            gold_amount=trans.amount,
            unit_price_irt=trans.unit_price_irt,
            currency=currency
        )

        with transaction.atomic():

            trans = Transaction.objects.select_for_update(skip_locked=True).filter(
                id=trans.id,
                status='pending'
            ).first()

            if trans is None:
                continue

            wallet = trans.wallet
            wallet_amount = abs(wallet.amount)
            customer = trans.customer
            last_price = CurrencyPriceLog.objects.filter(currency=currency).last()

            if last_price is None:
                logger.error(
                    f"[task=process_sell] No price log found — skipping | "
                    f"transaction_id={trans.id} currency={currency.symbol}"
                )
                continue

            customer_xau_balance = WalletSelector.get_user_balance_for_update(
                user_id=customer.user.id,
                wallet_type=Wallet.WALLETTYPES[1][0]
            )
            if customer_xau_balance < 0:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Negative XAU balance"
                trans.processed_at = now_ts
                trans.save()
                logger.warning(
                    f"[task=process_sell] Transaction REJECTED — negative XAU balance | "
                    f"transaction_id={trans.id} customer_id={customer.id}"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if transaction_total_price['total'] != trans.total_price_irt:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction total price is not match"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[1][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت فروش ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_sell] Transaction REJECTED — price mismatch | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"expected={transaction_total_price['total']} got={trans.total_price_irt} "
                    f"refund={wallet_amount}g XAU"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if trans.amount != wallet_amount:
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction amount is not match"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[1][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت فروش ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_sell] Transaction REJECTED — amount/wallet mismatch | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"trans_amount={trans.amount} wallet_amount={wallet_amount} "
                    f"refund={wallet_amount}g XAU"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if trans.unit_price_irt > last_price.price and abs(last_price.price - trans.unit_price_irt) > (trans.unit_price_irt / 100):
                trans.is_checked = True
                trans.status = Transaction.TRANSACTIONSTATUSES[2][0]
                trans.reject_reason = "Transaction unit price is not match with last price"
                trans.processed_at = now_ts
                trans.save()
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[1][0],
                    amount=wallet_amount,
                    desc=f"بابت برگشت فروش ناموفق: {currency.fa_title}",
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.warning(
                    f"[task=process_sell] Transaction REJECTED — unit price deviation >1% | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"order_price={trans.unit_price_irt} market_price={last_price.price} "
                    f"refund={wallet_amount}g XAU"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            trans.is_checked = True
            trans.status = Transaction.TRANSACTIONSTATUSES[1][0]
            trans.processed_at = now_ts
            trans.save()

            if trans.withdraw_method == Transaction.WITHDRAWTYPES[0][0]:  # Wallet
                Wallet.objects.create(
                    customer=customer,
                    wallet_type=Wallet.WALLETTYPES[0][0],
                    amount=trans.total_price_irt,
                    desc=f'فروش {currency.fa_title} به شماره فاکتور : {trans.id}',
                    created_at=now_ts,
                    verified_at=now_ts,
                    ip="1.1.1.1",
                    is_verified=True
                )
                logger.info(
                    f"[task=process_sell] Transaction SUCCESS — IRT credited to wallet | "
                    f"transaction_id={trans.id} customer_id={customer.id} "
                    f"gold={trans.amount}g irt={trans.total_price_irt}IRT"
                )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue

            if trans.withdraw_method == Transaction.WITHDRAWTYPES[1][0]:  # Bank
                customer_irt_balance = WalletSelector.get_user_balance_for_update(
                    user_id=customer.user.id,
                    wallet_type=Wallet.WALLETTYPES[0][0]
                )
                withdrawal = SettlementService.create_withdrawal_request(
                    customer=customer,
                    card=trans.card,
                    amount=trans.total_price_irt,
                    method='پایا',
                    remaining_wallet_amount=customer_irt_balance
                )
                logger.info(
                    f"[task=process_sell] Withdrawal request created for bank settlement | "
                    f"transaction_id={trans.id} withdrawal_id={withdrawal.id} "
                    f"customer_id={customer.id} amount={trans.total_price_irt}IRT"
                )
                try:
                    process_withdrawal_requests.apply_async(
                        args=[withdrawal.id],
                        countdown=10
                    )
                except Exception as e:
                    logger.error(
                        f"[task=process_sell] Failed to queue withdrawal task | "
                        f"transaction_id={trans.id} withdrawal_id={withdrawal.id} error={e}"
                    )
                transaction.on_commit(lambda: transaction_processed.send(
                    sender='exchange', transaction_id=trans.id, status=trans.status)
                )
                continue
