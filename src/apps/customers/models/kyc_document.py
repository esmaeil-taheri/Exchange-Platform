from django.db import models

from apps.core.utils.date_time_utils import to_jalali


class KycDocument(models.Model):

    class Type(models.TextChoices):
        NATIONAL_CARD = "national_card",

    kyc = models.ForeignKey(
        "customers.Kyc",
        on_delete=models.CASCADE,
        related_name="documents"
    )

    doc_type = models.CharField(
        max_length=30,
        choices=Type.choices
    )

    image_url = models.URLField(max_length=1000, verbose_name='Image Url')

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    verified = models.BooleanField(
        default=False
    )

    @property
    def uploaded_at_jalali(self):
        return to_jalali(self.uploaded_at)
