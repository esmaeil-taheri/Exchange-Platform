from apps.settlements.models.withdrawal import Withdrawal


class WithdrawalSelectors:
    """Selectors for withdrawal queries."""

    @staticmethod
    def get_customer_withdrawals(customer, status=None):
        """
        Get all withdrawals for a customer, optionally filtered by status.

        Args:
            customer: Customer object
            status: Optional status filter

        Returns:
            QuerySet: Filtered withdrawal querysets
        """
        queryset = Withdrawal.objects.filter(
            customer=customer
        ).select_related('customer', 'card')

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @staticmethod
    def get_withdrawal_by_id(withdrawal_id, customer):
        """
        Get a specific withdrawal by ID.

        Args:
            withdrawal_id: Withdrawal ID
            customer: customer to verify ownership

        Returns:
            Withdrawal: The withdrawal object or None
        """
        try:
            return Withdrawal.objects.select_related('customer', 'card').filter(
                id=withdrawal_id, customer=customer
            )
        except Withdrawal.DoesNotExist:
            return None
        