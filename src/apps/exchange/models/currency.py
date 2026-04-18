from django.db import models


class Currency(models.Model):

    symbol = models.CharField(max_length=10, verbose_name='Symbol')
    
    fa_title = models.CharField(max_length=50, verbose_name='Frasi Title')
    en_title = models.CharField(max_length=50, verbose_name='English Title')

    logo_url = models.URLField(verbose_name='Logo Url')
    about = models.TextField(blank=True, verbose_name='About')

    lowest_amount_buy = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Lowest Amount Can Buy'
    )
    lowest_amount_sell = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Lowest Amount Can Sell'
    )

    fixed_buy_fee_toman = models.BigIntegerField(
        default=0, verbose_name='Fixed Buy Fee Toman'
    )

    buy_fee_percent = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Buy Fee '
    )

    fixed_sell_fee_toman = models.BigIntegerField(
        default=0, verbose_name='Fixed Sell Fee Toman'
    )

    sell_fee_percent = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Sell Fee '
    )

    maintance_fee = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        verbose_name='Maintance Fee'
    )

    is_sell = models.BooleanField(default=False, verbose_name='Buy Is Enabled')
    is_buy = models.BooleanField(default=False, verbose_name='Sell Is Enabled')

    def __str__(self):
        return f'{self.en_title} : {self.symbol}'
