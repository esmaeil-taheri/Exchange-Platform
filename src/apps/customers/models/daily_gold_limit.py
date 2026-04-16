from django.db import models

from apps.core.utils.date_time_utils import to_jalali


class IncreaseDailyGoldLimit(models.Model):

    CELINGTYPE = [
        ('sell','Sell'),
        ('buy','Buy'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        verbose_name='Customer'
    )

    amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0, verbose_name='Amount'
    )

    limit_type = models.CharField(
        max_length=10, choices=CELINGTYPE, default="Other",
        verbose_name='Limit Type'
    )

    is_verifid = models.BooleanField(default=None, null=True, verbose_name='Is Verified') # None : waiting / True : Accept / False : Reject

    confirmed_by = models.ForeignKey(
        'admins.SiteAdmin', on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='Confirmed By'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    def __str__(self):
        return f'{self.customer.full_name}'

    @property
    def created_at_to_jalali(self):
        return to_jalali(self.created_at)