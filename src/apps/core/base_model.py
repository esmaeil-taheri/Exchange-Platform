from django.db import models


class SingletonModel(models.Model):
    """
    Ensures only ONE row exists.
    """

    class Meta:
        abstract = True

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
