
from apps.core.services.payment.zarrinpal import ZarinpalGateway
from apps.payments.models.invoice import Invoice

class PaymentService:

    gateway = ZarinpalGateway()

    @staticmethod
    def create_payment_gateway_link(amount: int, invoice_id: int) -> dict:
        return PaymentService.gateway.process_payment(
            amount=amount, invoice_id=invoice_id
        )
    
    @staticmethod
    def create_invoice():
         pass
        
