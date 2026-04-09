import time
import jdatetime

from django.db import models
from django.core.cache import cache


class SingletonModel(models.Model):
    """
    Ensures only ONE row exists.
    """

    class Meta:
        abstract = True

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class SiteSetting(SingletonModel):
    # Public
    site_name = models.CharField(max_length=100, default="My Project", verbose_name='Site Name')
    customer_register = models.BooleanField(default=True, verbose_name='Customer Register')
    customer_login = models.BooleanField(default=True, verbose_name='Customer Login')
    
    # Authentication
    check_mobile_ownership = models.BooleanField(default=False, verbose_name='Check Mobile Ownership')
    
    # Sms
    send_welcome_sms = models.BooleanField(default=False, verbose_name='Send Welome Message')
    send_login_alert_sms = models.BooleanField(default=False, verbose_name='Send Login Alret SMS')
    
    # System Metadata
    modified_timestamp = models.IntegerField(default=0, verbose_name='Modified Timestamp')

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Setting"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.modified_timestamp = int(time.time())
        super().save(*args, **kwargs)

        cache.delete("site_settings")

    def delete(self, *args, **kwargs):
        pass

    @property
    def shamsi_modified_at(self):
        return jdatetime.datetime.fromtimestamp(int(self.modified_timestamp))

    def __str__(self):
        return self.site_name