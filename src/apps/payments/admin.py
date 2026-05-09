from django.contrib import admin
from apps.payments.models.invoice import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'payment_gateway', 'gateway_tack_id',
    ]