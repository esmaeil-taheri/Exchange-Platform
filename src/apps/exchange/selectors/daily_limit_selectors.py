from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from apps.customers.models.increase_daily_limit import IncreaseDailyTransactionLimit
from apps.exchange.models.daily_transaction_limit import DailyTransactionLimit
from apps.exchange.models.transaction import Transaction


class DailyLimitSelector:

    @staticmethod
    def get_base_daily_limit():
        return DailyTransactionLimit.objects.first()

    @staticmethod
    def get_customer_daily_usage(customer, transaction_type):
        """Get total transactions for last 24 hours (unix timestamp version)"""

        # datetime → unix timestamp
        last_24_hours_dt = timezone.now() - timedelta(hours=24)
        last_24_hours_ts = int(last_24_hours_dt.timestamp())

        result = Transaction.objects.filter(
            customer=customer,
            transaction_type=transaction_type,
            status='success',
            created_at__gte=last_24_hours_ts
        ).aggregate(total=Sum('total_price_irt'))

        return result['total'] or 0

    @staticmethod
    def get_approved_limit_increases(customer, limit_type):
        """Get approved limit increases for today"""
        
        result = IncreaseDailyTransactionLimit.objects.filter(
            customer=customer,
            limit_type=limit_type,
            is_verifid=True,
        ).aggregate(total=Sum('amount'))
        
        return result['total'] or 0