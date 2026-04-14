from django.contrib import admin

from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc
from apps.customers.models.kyc_document import KycDocument
from apps.customers.models.bank_card import BankCard


class KycInlines(admin.StackedInline):
    model = Kyc
    verbose_name = 'Kyc Status'
    verbose_name_plural = 'Kyc Status'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name',
        'user_national_id',
        'user_phone',
        'user_last_ip',
        'status',
        'user_active_2fa'
    ]

    list_display_links = ['id', 'full_name']

    search_fields = [
        'id',
        'user__national_id',
        'user__phone_number',
        'user__first_name',
        'user__last_name'
    ]

    list_filter = [
        'status',
    ]

    ordering = ['-id']
    inlines = [KycInlines]

    list_select_related = ['user']
    raw_id_fields = ('user', )

    readonly_fields = [
        'full_name',
        'user_national_id',
        'user_phone'
    ]

    def full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    full_name.short_description = "Full Name"

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = "Phone"

    def user_national_id(self, obj):
        return obj.user.national_id
    user_national_id.short_description = "National ID"

    def user_last_ip(self, obj):
        return obj.user.last_ip_address
    user_last_ip.short_description = "IP Address"

    def user_active_2fa(self, obj):
        return obj.user.is_2fa_enabled
    user_active_2fa.short_description = "Active 2FA"


class KycDocumentInlines(admin.StackedInline):
    model = KycDocument
    verbose_name = 'Kyc Document'
    verbose_name_plural = 'Kyc Document'
    

@admin.register(Kyc)
class KycAdmin(admin.ModelAdmin):
    list_display = ['customer', 'government_verified', 'status', 'submitted_at', 'reviewed_by', 'reviewed_at',]

    readonly_fields = ['submitted_at', 'reviewed_at']

    inlines = [KycDocumentInlines]


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'bank_name', 'card_ownership', 'owner_information', 'is_verified', 'created_at_jalali']

    read_only_fields = ['modified_by']
    