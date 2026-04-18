from django.db import models

import jdatetime


class CurrencyPriceLog(models.Model):
    currency = models.ForeignKey(
        'exchange.Currency', on_delete=models.CASCADE, 
        verbose_name='Currency', related_name='price_logs'
    )
    price = models.IntegerField(default=0, verbose_name='Price')
    timestamp = models.IntegerField(default=0, verbose_name='Timestamp')

    def __str__(self):
        return f'{self.currency.symbol}: {self.price}'

    @property
    def shamsi_timestamp(self):
        return jdatetime.datetime.fromtimestamp(int(self.timestamp))