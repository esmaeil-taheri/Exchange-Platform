from django.db import models
from django.contrib.auth.models import (
    AbstractUser, BaseUserManager
)

import pyotp
import jdatetime

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=11, unique=True, verbose_name='Phone Number', default='-')
    national_id = models.CharField(max_length=10, unique=True, verbose_name="National ID", default='-')

    is_suspended = models.BooleanField(default=False, verbose_name='Is Suspended')
    phone_number_ownership = models.BooleanField(default=False, verbose_name='Mobile Ownership')

    otp = models.CharField(max_length=6, default='-', verbose_name='OTP')
    otp_expires_timestamp = models.IntegerField(default=0, verbose_name='OTP Expires')

    last_login_timestamp = models.IntegerField(default=0, verbose_name='Last Login')
    last_ip_address = models.GenericIPAddressField(default='0.0.0.0', verbose_name='Last Ip Address')

    is_2fa_enabled = models.BooleanField(default=False, verbose_name='Is 2FA Enabled')
    requires_2fa = models.BooleanField(default=False, verbose_name='Is 2FA Enabled')
    totp_secret = models.CharField(max_length=32, verbose_name='2FA Secret', blank=True)

    created_timestamp = models.IntegerField(default=0, verbose_name='Created On')

    class Meta:
        unique_together = [['phone_number', 'national_id', ]]

    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    def get_totp_uri(self):
        return pyotp.TOTP(self.totp_secret).provisioning_uri(
            name=self.national_id,
            issuer_name="Exchange"
        )
    
    def verify_totp(self, code):
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)
    
    @property
    def shamsi_last_login(self):
        return jdatetime.datetime.fromtimestamp(int(self.last_login_timestamp))
    
    @property
    def shamsi_otp_expires(self):
        return jdatetime.datetime.fromtimestamp(int(self.otp_expires_timestamp))
    
    @property
    def registration(self):
        return jdatetime.datetime.fromtimestamp(int(self.created_timestamp))

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
        
