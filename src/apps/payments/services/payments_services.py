from django.db import transaction

from apps.core.services.payment.zarrinpal import ZarinpalGateway
from apps.payments.selectors.payments_selectors import PaymentsSelectors
from apps.payments.models.invoice import Invoice
from apps.payments.exceptions.payments_exceptions import InvoiceNotFound
from apps.customers.models.bank_card import BankCard

import hashlib


class PaymentService:

    gateway = ZarinpalGateway()

    @staticmethod
    def create_invoice(
        customer,
        total_price: int,
        unit_price: int = 0,
        fee: int = 0,
        maintenance_fee: int = 0,
        invoice_type: str = Invoice.INVOICE_TYPES[0][0]
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
            invoice_type=invoice_type,
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

    @staticmethod
    def handle_zarinpal_callback(gateway_track_id: str, request) -> dict:
        """
        Handle the callback from Zarinpal payment gateway.
        
        Args:
            gateway_track_id: The tracking ID (authority) returned by Zarinpal
            request: The original request object
        
        Returns:
            dict: Response message for the user
        """

        invoice = PaymentsSelectors.get_invoice_by_authority(gateway_track_id)

        if not invoice:
            raise InvoiceNotFound('تراکنش یافت نشد')

        # Quick idempotency check (without lock)
        if invoice.is_paid:
            return {'message': 'این فاکتور قبلاً پرداخت شده است'}

        customer = invoice.customer

        verification_result = PaymentService.gateway.verify_payment(
            authority=gateway_track_id,
            amount=invoice.total_price
        )

        if verification_result == 101:
            return {'message': 'این فاکتور قبلاً پرداخت شده است'}
        
        if verification_result == 102:

            with transaction.atomic():

                invoice = PaymentsSelectors.get_invoice_by_id_for_update(
                    invoice_id=invoice.id
                )

                if invoice.is_paid:
                    return {'message': 'این فاکتور قبلاً پرداخت شده است'}

                invoice.status = Invoice.STATUS_CHOICES[2][0] # failed
                invoice.gateway_response = str(verification_result)

                invoice.save(update_fields=[
                    'status',
                    'gateway_response'
                ])

            return {'message': 'پرداخت ناموفق بود'}
        
        verify_data = verification_result.get('data', {})

        card_hash = verify_data.get('card_hash', '')
        card_pan = verify_data.get('card_pan', '')
        ref_id = verify_data.get('ref_id')

        customer_cards = BankCard.objects.filter(
            customer=customer,
            is_verified=True,
            is_show=True
        ).only('card_number')

        card_is_valid = False

        for card in customer_cards:

            card_number = card.card_number.strip()

            sha256_hash = hashlib.sha256(card_number.encode()).hexdigest().upper()
            sha512_hash = hashlib.sha512(card_number.encode()).hexdigest().upper()

            if card_hash in (sha256_hash, sha512_hash):
                card_is_valid = True
                break

            masked1 = f"{card_number[:6]}******{card_number[-4:]}"
            masked2 = f"{card_number[:6]}xxxxxx{card_number[-4:]}"

            if card_pan in (masked1, masked2):
                card_is_valid = True
                break

        with transaction.atomic():
            # Lock the row
            invoice = PaymentsSelectors.get_invoice_by_id_for_update(invoice_id=invoice.id)

            # Final idempotency check
            if invoice.is_paid:
                return {'message': 'این فاکتور قبلاً پرداخت شده است'}

            # Update based on card validation
            if card_is_valid:
                invoice.is_paid = True
                invoice.status = Invoice.STATUS_CHOICES[1][0] # successs
                message = 'پرداخت با موفقیت انجام شد'
            else:
                invoice.status = Invoice.STATUS_CHOICES[3][0]  # rejected
                message = 'کارت پرداخت کننده مجاز نیست'

            invoice.gateway_response = str(verification_result)
            invoice.card_hash = card_hash
            invoice.card_pan = card_pan
            invoice.ref_id = ref_id

            invoice.save(update_fields=[
                'is_paid',
                'status',
                'gateway_response',
                'card_hash',
                'card_pan',
                'ref_id'
            ])

        return {'message': message}

    @staticmethod
    def initiate_deposit(amount: int, request) -> dict:
        """
        Initiate a deposit transaction for the user.

        Args:
            amount: Amount to be deposited (in Rials)
            request: The original request object

        Returns:
            dict: Contains authority and payment_link for the deposit
        """
        customer = request.user.customer_profile
        
        invoice = PaymentService.create_invoice(
            customer=customer,
            total_price=amount,
            invoice_type=Invoice.INVOICE_TYPES[0][0]  # deposit
        )
        try:
            payment_data = PaymentService.create_payment_gateway_link(
                amount=amount,
                invoice_id=invoice.id
            )
        except Exception:
            invoice.gateway_response = "gateway_failed"
            invoice.status = "failed"
            invoice.save(update_fields=["gateway_response", "status"])
            raise

        authority = payment_data['authority']
        payment_link = payment_data['payment_link']

        invoice.payment_gateway = 'zari'
        invoice.gateway_track_id = authority

        invoice.save(update_fields=['payment_gateway', 'gateway_track_id'])

        return {'message': payment_link}

