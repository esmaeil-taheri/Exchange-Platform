from django.db import models

from apps.core.base_model import SingletonModel
from apps.core.utils.date_time_utils import to_jalali


class DailyTransactionLimit(SingletonModel):

    buy_amount = models.BigIntegerField(
        default=0, verbose_name='Buy Limit'
    )
    sell_amount = models.BigIntegerField(
        default=0, verbose_name='Sell Limit'
    )

    modified_by = models.ForeignKey(
        'admins.SiteAdmin', on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='Modified By'
    )

    modified_at = models.DateTimeField(
        auto_now=True, verbose_name='Modified At'
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Buy: {self.buy_amount} | Sell: {self.sell_amount}'
    
    @property
    def modified_at_to_jalali(self):
        return to_jalali(self.modified_at)
