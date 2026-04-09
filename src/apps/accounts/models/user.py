from django.db import models
from django.contrib.auth.models import (
    AbstractUser, BaseUserManager
)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, max_length=255, blank=True)

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.username
