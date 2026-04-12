from django.db import models
from django.conf import settings

from apps.core.utils.date_time_utils import to_jalali


class SiteAdmin(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='User', related_name='admin_profile'
    )
    is_otp_enabled = models.BooleanField(default=False, verbose_name='Enabled OTP')

    nick_name = models.CharField(max_length=100, verbose_name='Nickname')
    position = models.CharField(max_length=50, verbose_name='Position')
    about = models.TextField(verbose_name='About', blank=True)
    personal_code = models.CharField(max_length=4, verbose_name='Personal Code', unique=True)
    profile_pic = models.URLField(verbose_name='Profile Picture')

    allowed_ips = models.ManyToManyField('admins.TrustedIp', blank=True, verbose_name='Allowed IPs')

    @property
    def jalali_last_login(self):
        return to_jalali(self.user.last_login)

    def __str__(self):
        return self.user.get_full_name()