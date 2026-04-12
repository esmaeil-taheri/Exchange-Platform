from django.db import models

from apps.core.utils.date_time_utils import to_jalali


class Kyc(models.Model):

    class Status(models.TextChoices):
        NOT_STARTED = "not_started",
        GOV_VERIFIED = "gov_verified",
        DOCUMENT_UPLOADED = "document_uploaded",
        PENDING_REVIEW = "pending_review",
        REJECTED = "rejected",
        APPROVED = "approved",

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="kyc"
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )

    government_verified = models.BooleanField(
        default=False
    )

    reviewed_by = models.ForeignKey(
        "admins.SiteAdmin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejection_reason = models.TextField(
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "KYC"
        verbose_name_plural = "KYCs"

    @property
    def submitted_at_jalali(self):
        return to_jalali(self.submitted_at)
    
    @property
    def reviewed_at_jalali(self):
        return to_jalali(self.reviewed_at)
    

    def __str__(self):
        return f"KYC - {self.customer}"
    

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

    image_url = models.URLField(verbose_name='Image Url')

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    verified = models.BooleanField(
        default=False
    )

    @property
    def uploaded_at_jalali(self):
        return to_jalali(self.uploaded_at)
    