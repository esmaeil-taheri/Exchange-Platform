from .base import *
from decouple import config

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True
