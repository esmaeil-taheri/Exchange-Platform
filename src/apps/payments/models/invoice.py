from django.db import models


class Invoice(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    )

    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE, related_name='invoices', verbose_name='Customer')

    payment_gateway = models.CharField(
        max_length=255, blank=True, verbose_name='Payment Gateway')
    gateway_tack_id = models.CharField(
        max_length=255, blank=True, verbose_name='Gateway Track ID')
    gateway_response = models.TextField(
        blank=True, verbose_name='Gateway Response')

    unit_price = models.BigIntegerField(default=0, verbose_name='Unit Price')
    fee = models.IntegerField(default=0, verbose_name='Fee')
    maintenance_fee = models.IntegerField(
        default=0, verbose_name='Maintenance Fee')
    total_price = models.BigIntegerField(default=0, verbose_name='Total Price')

    is_paid = models.BooleanField(default=False, verbose_name='Is Paid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_CHOICES[0][0], verbose_name='Status')

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f"Invoice {self.id} - Customer: {self.customer.user.username}"
