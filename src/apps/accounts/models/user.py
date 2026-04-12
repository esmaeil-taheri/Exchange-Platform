from django.db import models
from django.contrib.auth.models import AbstractUser


from apps.core.utils.date_time_utils import to_jalali

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=50, default='New', verbose_name="First Name")
    last_name = models.CharField(max_length=50, default='User', verbose_name="Last Name")

    phone_number = models.CharField(max_length=11, unique=True, verbose_name='Phone Number', default='-')
    national_id = models.CharField(max_length=10, verbose_name="National ID", default='-')

    is_suspended = models.BooleanField(default=False, verbose_name='Is Suspended')

    last_login = models.DateTimeField(auto_now_add=True, verbose_name='Last Login')
    last_ip_address = models.GenericIPAddressField(default='0.0.0.0', verbose_name='Last Ip Address')

    is_2fa_enabled = models.BooleanField(default=False, verbose_name='Is 2FA Enabled')
    requires_2fa = models.BooleanField(default=False, verbose_name='Requires 2FA')
    totp_secret = models.CharField(max_length=32, verbose_name='2FA Secret', blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        unique_together = [['phone_number', 'national_id', ]]

    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    @property
    def created_at_jalali(self):
        return to_jalali(self.created_at)
    
    @property
    def last_login_jalali(self):
        return to_jalali(self.last_login)
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'
        