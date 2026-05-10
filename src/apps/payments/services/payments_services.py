
from apps.core.services.payment.zarrinpal import ZarinpalGateway
from apps.payments.models.invoice import Invoice


class PaymentService:

    gateway = ZarinpalGateway()

    @staticmethod
    def create_invoice(
        customer,
        total_price: int,
        unit_price: int = 0,
        fee: int = 0,
        maintenance_fee: int = 0,
    ) -> Invoice:
        """
        Create a new invoice for a payment transaction.

        Args:
            customer: Customer object
            total_price: Total amount to be paid (in Rials)
            unit_price: Unit price of the asset
            fee: Transaction fee
            maintenance_fee: Maintenance fee

        Returns:
            Invoice: The created invoice object
        """
        invoice = Invoice.objects.create(
            customer=customer,
            unit_price=unit_price,
            fee=fee,
            maintenance_fee=maintenance_fee,
            total_price=total_price,
            status='pending',
            is_paid=False,
        )
        return invoice

    @staticmethod
    def create_payment_gateway_link(amount: int, invoice_id: int) -> dict:
        """
        Create a payment gateway link for the invoice.

        Args:
            amount: Payment amount in Rials
            invoice_id: Invoice ID

        Returns:
            dict: Contains authority and payment_link
        """
        return PaymentService.gateway.process_payment(
            amount=amount, invoice_id=invoice_id
        )
