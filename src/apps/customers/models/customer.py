from django.db import models
from django.conf import settings

class Customer(models.Model):

    CUSTOMERGENDER = [
        ('unknown', '?'),
        ('male','Male'),
        ('female','Female') 
    ]

    CUSTOMERLEVEL = [
        ('br', 'Boronze'),
        ('si', 'Silver'),
        ('go', 'Gold')
    ]

    CUSTOMERSTATUS = [
        ('preregister', 'PreRegister'),
        ('suspended', 'Suspended'),
        ('authenticated', 'Authenticated')
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
        verbose_name='User', related_name='customer_profile'
    )

    status = models.CharField(max_length=50, choices=CUSTOMERSTATUS, default=CUSTOMERSTATUS[0][0], verbose_name='Status')
    level = models.CharField(max_length=50, choices=CUSTOMERLEVEL, default=CUSTOMERLEVEL[0][0], verbose_name='Level')

    referral_code = models.CharField(max_length=12, verbose_name='Referral Code', blank=True)
    used_referral_code = models.CharField(max_length=12, verbose_name='Used Referral Code', blank=True)

    birth_date = models.CharField(max_length=10, default="-", verbose_name='Birthday')
    gender = models.CharField(max_length=7, choices=CUSTOMERGENDER, default=CUSTOMERGENDER[0][0], verbose_name='Gender')
    father_name = models.CharField(max_length=25, blank=True, default='Adam')

    def __str__(self):
        return self.user.get_full_name()

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def kyc_overall_rate(self):
        steps = (
            self.uploaded_id_card,
            self.rules_accepted,
            self.information_completion,
            self.auth_check_ready,
        )
        return int(sum(steps) / len(steps) * 100)
