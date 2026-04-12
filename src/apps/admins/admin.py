from django.contrib import admin

from apps.admins.models.site_admin import SiteAdmin
from apps.admins.models.trusted_ip import TrustedIp


@admin.register(TrustedIp)
class TrustedIpAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'ip']
    search_fields = ['title', 'ip']


@admin.register(SiteAdmin)
class SiteAdminAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'first_name',
        'last_name',
        'national_id',
        'nick_name',
        'position',
        'last_ip',
        'jalali_last_login',
    )

    list_display_links = ['id', 'national_id']

    search_fields = [
        'id',
        'user__national_id',
        'user__phone_number',
        'user__first_name',
        'user__last_name'
    ]

    list_select_related = ['user']

    fieldsets = (
        (None, {
            'fields': (
                'user',
                'nick_name',
                'position',
                'about',
                'personal_code'
            )
        }),

        ('Security', {
            'fields': (
                'is_otp_enabled',
                'allowed_ips'
            )
        }),

        ('Appearance', {
            'fields': ('profile_pic',)
        }),
    )

    # -------- user fields --------

    def first_name(self, obj):
        return obj.user.first_name
    first_name.short_description = "First Name"

    def last_name(self, obj):
        return obj.user.last_name
    last_name.short_description = "Last Name"

    def national_id(self, obj):
        return obj.user.national_id
    national_id.short_description = "National ID"

    def last_ip(self, obj):
        return obj.user.last_ip_address
    last_ip.short_description = "Last IP"
