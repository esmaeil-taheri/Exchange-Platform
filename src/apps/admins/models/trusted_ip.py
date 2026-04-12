from django.db import models


class TrustedIp(models.Model):
    title = models.CharField(max_length=255, verbose_name='Title')
    ip = models.GenericIPAddressField(verbose_name='IP Address')
    
    def __str__(self):
        return f'{self.title} | {self.ip}'