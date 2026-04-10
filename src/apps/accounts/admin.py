from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.admins.models.site_admin import SiteAdmin
from apps.customers.models.customer import Customer

from .models import CustomUser

class CustomerInlines(admin.StackedInline):
    model = Customer
    verbose_name = 'Customer Profile'
    verbose_name_plural = 'Customer Profile'


class SiteAdminInlines(admin.StackedInline):
    model = SiteAdmin
    verbose_name = 'Admin Profile'
    verbose_name_plural = 'Admin Profile'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide', ),
                'fields': (
                    'username', 'usable_password', 'password1', 'password2',
                    'phone_number', 'national_id', 'is_suspended',
                    'last_login_jalali', 'last_ip_address',
                    'is_2fa_enabled', 'requires_2fa', 'totp_secret',
                )
            }
        ),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('Authentication', {
            'fields': (
                'created_at_jalali',
                'last_login_jalali',
                'last_ip_address',
                'is_suspended',
                'is_2fa_enabled', 'requires_2fa', 'totp_secret',

            ) 
        }),
        ('Personal Info', {'fields': (
            'first_name', 'last_name', 'email', 'phone_number', 'national_id')}),
    )

    readonly_fields = [
        'created_at_jalali',
        'last_login_jalali',
        'last_ip_address',
        'totp_secret'
    ]

    list_display_links = ['id', 'national_id']

    list_display = ('id', '__str__', 'phone_number', 'national_id', 'is_2fa_enabled',
                    'is_suspended', 'last_ip_address', 'last_login_jalali', )
    
    inlines = [CustomerInlines, SiteAdminInlines]
    
    search_fields = ['id', 'national_id', 'phone_number', 'first_name', 'last_name']
    