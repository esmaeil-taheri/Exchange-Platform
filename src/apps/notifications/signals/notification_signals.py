from django.dispatch import receiver

from apps.notifications.services.notification_services import NotificationService
from apps.accounts.services.user_services import login_detected
from apps.exchange.tasks.exchange_tasks import transaction_processed


@receiver(login_detected)
def handle_user_login(sender, user, *args, **kwargs):
    NotificationService.create_notification_from_template(
        template_code='LOGIN_ALERT',
        user=user,
        context={
            'date': user.last_login.strftime('%Y-%m-%d %H:%M'),
            'ip': user.last_ip_address
        }
    )


@receiver(transaction_processed, sender='exchange')
def handle_transaction_processed(sender, transaction_id, status, *args, **kwargs):
    from apps.exchange.models.transaction import Transaction
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        customer = transaction.customer
    except Transaction.DoesNotExist:
        return

    if status == Transaction.TRANSACTIONSTATUSES[2][0]:  # Rejected
        NotificationService.create_notification_from_template(
            template_code='TRANSACTION_REJECTED',
            user=transaction.customer.user,
            context={
                'transaction_id': transaction.id,
                'customer_name': customer.user.first_name,
            }
        )   

    if status == Transaction.TRANSACTIONSTATUSES[1][0]:  # Completed
        NotificationService.create_notification_from_template(
            template_code='TRANSACTION_COMPLETED',
            user=transaction.customer.user,
            context={
                'transaction_id': transaction.id,
                'customer_name': customer.user.first_name,
            }
        )
