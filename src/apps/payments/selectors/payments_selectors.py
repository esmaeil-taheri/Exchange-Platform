from apps.payments.models.invoice import Invoice

class PaymentsSelectors:

    @staticmethod
    def get_invoice_by_authority(authority: str):
        
        try:
            return Invoice.objects.prefetch_related('customer').get(
                gateway_track_id=authority, status__in=('pending', 'paid')
            )
        except Invoice.DoesNotExist:
            return None
    
    @staticmethod
    def get_invoice_by_id_for_update(invoice_id: int):
        return Invoice.objects.select_for_update().get(id=invoice_id)
