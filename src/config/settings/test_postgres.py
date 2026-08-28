"""
Test settings against a real PostgreSQL server.

Everything is inherited from `test` (LocMemCache, eager Celery, silent logging);
only the two things that make SQLite unfit for verifying financial code are
overridden:

  * a real PostgreSQL connection — SQLite silently drops `SELECT ... FOR UPDATE`,
    so the customer row locks the buy/sell/withdrawal paths rely on are never
    exercised there, and `TestRealRowLocks` skips itself.
  * the real migration chain — `test` creates tables straight from the models,
    so a broken migration would never be caught.

Used by the `test-postgres` CI job.
"""

from .test import *  # noqa: F403
from .base import DATABASES  # noqa: F401  — the env-driven PostgreSQL config

# `test` replaces this with a stub that disables migrations; restore the default
# so the migration chain actually runs.
MIGRATION_MODULES = {}
