from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide', ),
                'fields': (
                    'username', 'usable_password', 'password1', 'password2',
                    'phone_number', 'national_id', 'is_suspended', 'otp',
                    'otp_expires_timestamp', 'last_login_timestamp', 'last_ip_address',
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
                'registration',
                'shamsi_last_login', 'shamsi_otp_expires', 'last_ip_address',
                'is_suspended', 'phone_number_ownership',
                'otp', 'otp_expires_timestamp', 'last_login_timestamp',
                'is_2fa_enabled', 'requires_2fa', 'totp_secret',

            ) 
        }),
        ('Personal Info', {'fields': (
            'first_name', 'last_name', 'email', 'phone_number', 'national_id')}),
    )

    readonly_fields = [
        'registration',
        'shamsi_last_login',
        'shamsi_otp_expires',
        'last_ip_address',
        'totp_secret'
    ]

    list_display_links = ['id', 'national_id']

    list_display = ('id', '__str__', 'phone_number', 'national_id', 'is_2fa_enabled',
                    'is_suspended', 'phone_number_ownership', 'last_ip_address', 'otp', 'shamsi_last_login', )
    
    search_fields = ['id', 'national_id', 'phone_number', 'first_name', 'last_name']
    