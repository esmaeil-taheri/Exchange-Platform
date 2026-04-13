from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.db import transaction

from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc
from apps.core.utils.general_utils import create_random_link


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_for_user(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            customer = Customer.objects.create(
                user=instance,
                referral_code=create_random_link()
            )
            Kyc.objects.create(customer=customer)