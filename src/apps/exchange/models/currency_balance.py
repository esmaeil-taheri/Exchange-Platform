from django.db import models

from apps.core.utils.date_time_utils import to_jalali


class CurrencyBalance(models.Model):

    currency = models.OneToOneField(
        'exchange.Currency', on_delete=models.CASCADE,
        verbose_name='Currency'
    )

    modified_by = models.ManyToManyField(
        'admins.SiteAdmin', blank=True,
        verbose_name='Modified By'
    )

    active_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Active Balance'
    )
    
    locked_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Locked Balance'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    modified_at = models.DateTimeField(auto_now=True, verbose_name='Modified At')

    def __str__(self):
        return f'{self.currency.en_title} Balance'
    
    @property
    def total_balance(self):
        return self.active_balance + self.locked_balance

    @property
    def created_at_to_jalali(self):
        return to_jalali(self.created_at)
    
    @property
    def modified_at_to_jalali(self):
        return to_jalali(self.modified_at)

    @property
    def modified_by_label(self):
        return 'admin' if self.modified_by.exists() else 'robot'
