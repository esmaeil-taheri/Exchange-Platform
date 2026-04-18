from django.db import models

import jdatetime


class Transaction(models.Model):
    TRANSACTIONTYPES = [
        ('buy','Buy'),
        ('sell','Sell'),
    ]

    TRANSACTIONSTATUSES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('rejected', 'Rejected')
    )
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        verbose_name='Customer', related_name='transactions'
    )
    currency = models.ForeignKey(
        'exchange.Currency', on_delete=models.SET_NULL,
        verbose_name='currency', related_name='transactions',
        null=True
    )
    # order = models.ForeignKey(
    #     'exchange.Order', on_delete=models.SET_NULL,
    #     verbose_name='Order', related_name='transaction',
    #     null=True, blank=True
    # )
    wallet = models.ForeignKey(
        'exchange.Wallet', on_delete=models.SET_NULL,
        verbose_name='Wallet', related_name='transaction',
        null=True
    )

    amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0, verbose_name='Amount'
    )
    fee_amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0, verbose_name='Fee'
    )

    fee_irt = models.BigIntegerField(default=0, verbose_name='Fee IRT')
    unit_price_irt = models.BigIntegerField(default=0, verbose_name='Unit Price IRT')
    total_price_irt = models.BigIntegerField(default=0, verbose_name='Total Price IRT')

    ip = models.GenericIPAddressField(default='0.0.0.0', verbose_name='Ip Address')

    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTIONTYPES, 
        default=TRANSACTIONTYPES[0][0], verbose_name='Transaction Type'
    )
    status = models.CharField(
        max_length=10, choices=TRANSACTIONSTATUSES, 
        default=TRANSACTIONSTATUSES[0][0], verbose_name='Status'
    )

    gateway_buy = models.BooleanField(default=False, verbose_name='Gateway Buy')

    created_at = models.BigIntegerField(default=0, verbose_name='Created At')
    processed_at = models.BigIntegerField(default=0, verbose_name='Processed At')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return str(self.pk)

    @property
    def shamsi_created(self):
        if self.created_at:
            return jdatetime.datetime.fromtimestamp(self.created_at).strftime("%Y/%m/%d %H:%M:%S")
        return "-"

    @property
    def shamsi_processed(self):
        if self.processed_at:
            return jdatetime.datetime.fromtimestamp(self.processed_at).strftime("%Y/%m/%d %H:%M:%S")
        return "-"

    @property
    def farsi_type(self):
        return 'خرید از ما' if self.transaction_type == 'buy' else 'فروش به ما'

    @property
    def farsi_status(self):
        mapping = {
            'pending': 'در انتظار',
            'success': 'موفق',
            'rejected': 'ناموفق'
        }
        return mapping.get(self.status, '-') 
