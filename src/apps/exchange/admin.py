from django.contrib import admin

from apps.exchange.models.currency import Currency
from apps.exchange.models.currency_balance import CurrencyBalance
from apps.exchange.models.price_log import CurrencyPriceLog
from apps.exchange.models.wallet import Wallet
from apps.exchange.models.transaction import Transaction
from apps.exchange.models.daily_transaction_limit import DailyTransactionLimit


admin.site.register(DailyTransactionLimit)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [ 'currency', 'customer', 'ip', 'amount', 'transaction_type', 'status', 'gateway_buy', 'shamsi_created']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['customer', 'ip', 'amount', 'wallet_type', 'is_verified', 'is_rejected']


@admin.register(CurrencyBalance)
class CurrencyBalanceAdmin(admin.ModelAdmin):
    list_display = ['currency', 'active_balance', 'locked_balance', 'total_balance', 'modified_at_to_jalali']


@admin.register(CurrencyPriceLog)
class CurrencyPriceLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'shamsi_timestamp']

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_sell', 'is_buy']
