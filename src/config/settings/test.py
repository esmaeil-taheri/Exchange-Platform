from .dev import *

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ── Disable migrations — create tables directly from models ──────────────────
# This skips migrations and creates database tables directly from models.
# Prevents SQLite from failing due to PostgreSQL-specific migrations.
class _DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = _DisableMigrations()

# ── Caches — LocMemCache (no Redis required) ──────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default",
    },
    "otp": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "otp",
    },
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ratelimit",
    },
}

# ── Celery — run tasks synchronously during tests ────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── Silence logging noise during tests ───────────────────────────────────────
LOGGING = {}
