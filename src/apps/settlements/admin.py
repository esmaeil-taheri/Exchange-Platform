from django.contrib import admin

from apps.settlements.models.withdrawal import Withdrawal

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = [
        'customer',
        'amount',
        'card',
        'status',
        'created_at'
    ]