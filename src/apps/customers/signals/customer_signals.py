from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apps.customers.models.customer import Customer
from apps.customers.models.kyc import Kyc


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_for_user(sender, instance, created, **kwargs):
    if created:
        customer = Customer.objects.create(user=instance)
        Kyc.objects.create(customer=customer)