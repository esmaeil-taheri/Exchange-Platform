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
    list_display = [
        'currency', 'customer', 'amount', 
        'formatted_total_price_irt',  
        'transaction_type', 'deposit_method',
        'withdraw_method', 'is_checked', 
        'status', 'ip', 'shamsi_created', 
        'shamsi_processed'
    ]


    def formatted_total_price_irt(self, obj):
        if obj.total_price_irt is None:
            return "-"
        return f"{obj.total_price_irt:,}"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['customer', 'ip', 'formatted_amount', 'wallet_type', 'is_verified', 'is_rejected', 'shamsi_created']

    def formatted_amount(self, obj):
        if obj.wallet_type == 'irt':
            return f"{int(obj.amount):,}"
        return obj.amount


@admin.register(CurrencyBalance)
class CurrencyBalanceAdmin(admin.ModelAdmin):
    list_display = ['currency', 'active_balance', 'locked_balance', 'total_balance', 'modified_at_to_jalali']


@admin.register(CurrencyPriceLog)
class CurrencyPriceLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'shamsi_timestamp']

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_sell', 'is_buy']
