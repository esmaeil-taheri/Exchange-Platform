from django.db import models


class Wallet(models.Model):

    WALLETTYPES = [
        ('irt', 'Toman'),
        ('xau', 'Gold')
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE, 
        verbose_name='Customer', related_name='wallets'
    )
    wallet_type = models.CharField(
        max_length=3, choices=WALLETTYPES, 
        default=WALLETTYPES[0][0], verbose_name='Wallet Type'
    )

    amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0, verbose_name='Amount'
    )
    desc = models.CharField(max_length=350, blank=True, verbose_name='Description')

    is_verified = models.BooleanField(default=False, verbose_name='Is Verified')
    verified_at = models.DateTimeField(blank=True, null=True, verbose_name='Verified At')

    is_rejected = models.BooleanField(default=False, verbose_name='Is Rejected')
    reject_reson = models.CharField(max_length=350, blank=True, verbose_name='Rejected Reason')

    ip = models.GenericIPAddressField(default='0.0.0.0', verbose_name='Ip Address')
    created_at =  models.BigIntegerField(verbose_name='Created at Timestamp')

    modified_by = models.ForeignKey(
        'admins.SiteAdmin', on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='Modified By'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['wallet_type']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['is_rejected']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.wallet_type.upper()} {round(self.amount, 4)}"
