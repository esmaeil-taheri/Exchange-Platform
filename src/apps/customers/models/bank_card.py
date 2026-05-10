from django.db import models

from apps.core.utils.date_time_utils import to_jalali


class BankCard(models.Model):
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='cards')

    bank_name = models.CharField(max_length=50, verbose_name='Bank Name')
    card_number = models.CharField(max_length=16, verbose_name='Card Number')
    account_number = models.CharField(max_length=30, default="-", verbose_name='Account Number')
    Shaba_number = models.CharField(max_length=50, default="-", verbose_name='Shaba Number')

    is_verified = models.BooleanField(default=None, null=True, verbose_name='Is Verified')  # None : waiting / True : Accept / False : Reject
    card_ownership = models.BooleanField(default=False, verbose_name='Ownership')
    owner_information = models.BooleanField(default=False, verbose_name='Owner Information')
    is_show = models.BooleanField(default=True, verbose_name='Show To Customer')

    modified_by = models.ForeignKey(
        'admins.SiteAdmin', 
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Modified By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    reject_reason = models.CharField(max_length=255, blank=True, verbose_name="Reject Reason")
    ownership_counter = models.IntegerField(default=0, verbose_name="Ownership Counter")
    information_counter = models.IntegerField(default=0, verbose_name='Information Counter')
    check_again_on = models.DateTimeField(verbose_name='Check On')

    @property
    def user_fullname(self):
        return self.customer.full_name
    
    @property
    def created_at_jalali(self):
        return to_jalali(self.created_at)
    
    @property
    def check_again_jalali(self):
        return to_jalali(self.check_again)

    def __str__(self):
        return self.card_number