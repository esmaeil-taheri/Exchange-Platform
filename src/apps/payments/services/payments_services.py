from django.db import transaction

from apps.core.services.payment.zarrinpal import ZarinpalGateway
from apps.payments.selectors.payments_selectors import PaymentsSelectors
from apps.payments.models.invoice import Invoice
from apps.payments.exceptions.payments_exceptions import InvoiceNotFound
from apps.customers.models.bank_card import BankCard
from apps.payments.tasks.payment_tasks import process_buy_invoice_task, process_deposit_invoice_task

import hashlib

from apps.core.utils.logger import get_logger

logger = get_logger(__name__)


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

        logger.info(
            f"Invoice created | invoice_id={invoice.id} customer_id={customer.id} "
            f"type={invoice_type} total={total_price}IRT fee={fee}IRT"
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

        logger.info(f"Zarinpal callback received | authority={gateway_track_id}")

        invoice = PaymentsSelectors.get_invoice_by_authority(gateway_track_id)

        if not invoice:
            logger.warning(f"Zarinpal callback — invoice not found | authority={gateway_track_id}")
            raise InvoiceNotFound('تراکنش یافت نشد')

        # Quick idempotency check (without lock)
        if invoice.is_paid:
            logger.info(
                f"Zarinpal callback — invoice already paid (idempotent) | "
                f"invoice_id={invoice.id} authority={gateway_track_id}"
            )
            return {'message': 'این فاکتور قبلاً پرداخت شده است'}

        customer = invoice.customer

        verification_result = PaymentService.gateway.verify_payment(
            authority=gateway_track_id,
            amount=invoice.total_price
        )

        if verification_result == 101:
            # 101 means Zarinpal already verified this payment, so the money is
            # captured. Reaching here means it was captured but never finalized
            # on our side — get_invoice_by_authority only returns pending
            # invoices. That is the crash window between the verify call above
            # and the commit further down (deploy, worker restart, OOM).
            #
            # verify_payment returns only the code on 101, never the card data,
            # so the card-ownership rule cannot be checked. Rejecting is
            # therefore the only safe outcome, and it must be loud: this is the
            # one state in the system where money is held pending a human.
            # is_paid deliberately stays False — process_stuck_invoices claims
            # on is_paid=True and would deliver the gold with no card check.
            with transaction.atomic():
                invoice = PaymentsSelectors.get_invoice_by_id_for_update(
                    invoice_id=invoice.id
                )

                if invoice.is_paid:
                    return {'message': 'این فاکتور قبلاً پرداخت شده است'}

                invoice.status = Invoice.STATUS_CHOICES[3][0]  # rejected
                invoice.gateway_response = (
                    'zarinpal_101_already_verified — captured but not finalized'
                )
                invoice.save(update_fields=['status', 'gateway_response'])

            logger.error(
                f"Payment captured but not finalized — needs manual review | "
                f"invoice_id={invoice.id} customer_id={invoice.customer_id} "
                f"authority={gateway_track_id} amount={invoice.total_price}IRT"
            )
            return {
                'message': (
                    f'پرداخت شما ثبت شده اما نیاز به بررسی دارد. '
                    f'لطفاً با پشتیبانی تماس بگیرید — شماره پیگیری: {invoice.id}'
                )
            }
        
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
                invoice.status = Invoice.STATUS_CHOICES[1][0]  # paid
                message = 'پرداخت با موفقیت انجام شد'
                logger.info(
                    f"Payment verified and accepted | invoice_id={invoice.id} "
                    f"customer_id={invoice.customer_id} ref_id={ref_id} "
                    f"amount={invoice.total_price}IRT card_pan={card_pan}"
                )
            else:
                invoice.status = Invoice.STATUS_CHOICES[3][0]  # rejected
                message = 'کارت پرداخت کننده مجاز نیست'
                logger.warning(
                    f"Payment rejected — card hash mismatch | invoice_id={invoice.id} "
                    f"customer_id={invoice.customer_id} card_pan={card_pan}"
                )

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
        
        try:
            if invoice.invoice_type == Invoice.INVOICE_TYPES[0][0]:  # deposit
                process_deposit_invoice_task.apply_async(
                    args=[invoice.id],
                    retry=True,
                    retry_policy={
                        'max_retries': 3,
                        'interval_start': 5,
                        'interval_step': 10,
                    }
                )
            elif invoice.invoice_type == Invoice.INVOICE_TYPES[1][0]:  # buy
                process_buy_invoice_task.apply_async(
                    args=[invoice.id],
                    retry=True,
                    retry_policy={
                        'max_retries': 3,
                        'interval_start': 5,
                        'interval_step': 10,
                    }
                )

            return {'message': message}
        
        except Exception as e:
            logger.error(
                f"Failed to queue processing task | invoice_id={invoice.id} "
                f"type={invoice.invoice_type} error={e}"
            )
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

        logger.info(
            f"Deposit request received | customer_id={customer.id} "
            f"user_id={request.user.id} amount={amount}IRT"
        )
        
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

            logger.error(
                f"Gateway creation failed | invoice_id={invoice.id} "
                f"customer_id={customer.id} amount={amount}IRT"
            )

            raise

        authority = payment_data['authority']
        payment_link = payment_data['payment_link']

        invoice.payment_gateway = 'zari'
        invoice.gateway_track_id = authority

        invoice.save(update_fields=['payment_gateway', 'gateway_track_id'])


        logger.info(
            f"Payment gateway created | invoice_id={invoice.id} "
            f"customer_id={customer.id} authority={authority} "
            f"amount={amount}IRT gateway=zari"
        )


        return {'message': payment_link}

