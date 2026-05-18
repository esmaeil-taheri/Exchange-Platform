"""
Logging Configuration — XAU18 Exchange Platform

Log format:
    2026-05-18 10:30:45,123 | INFO     | req=8f3a2b1c | user=42   | apps.exchange.services | message | key=value

Log files:
    logs/app.log       — All logs with level INFO and above
    logs/security.log  — Security-related events (OTP, payments, cards)
    logs/celery.log    — Celery task logs
    logs/errors.log    — Only ERROR and CRITICAL logs
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "req=%(request_id)-8s | user=%(user_id)-6s | "
    "%(name)s | %(message)s"
)

SIMPLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    # ─── Filters ────────────────────────────────────────────────────────────
    "filters": {
        "request_context": {
            "()": "apps.core.utils.logger.RequestContextFilter",
        },
    },

    # ─── Formatters ─────────────────────────────────────────────────────────
    "formatters": {
        "verbose": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": SIMPLE_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "colored": {
            "()": "apps.core.utils.log_formatter.ColoredFormatter",
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    # ─── Handlers ───────────────────────────────────────────────────────────
    "handlers": {
        # Console — for development
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
            "filters": [],
        },

        # Main file — all logs with level INFO
        "app_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "app.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "encoding": "utf-8",
            "formatter": "verbose",
            "filters": ["request_context"],
        },

        # Security file — sensitive events
        "security_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "security.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 90,
            "encoding": "utf-8",
            "formatter": "verbose",
            "filters": ["request_context"],
        },

        # Celery tasks file
        "celery_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "celery.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "encoding": "utf-8",
            "formatter": "verbose",
            "filters": ["request_context"],
        },

        # Errors file — only ERROR and CRITICAL
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "errors.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 90,
            "encoding": "utf-8",
            "formatter": "verbose",
            "level": "ERROR",
            "filters": ["request_context"],
        },
    },

    # ─── Loggers ────────────────────────────────────────────────────────────
    "loggers": {

        # Authentication — OTP, JWT, 2FA
        "apps.accounts": {
            "handlers": ["console", "app_file", "security_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },

        # Customer profile, KYC, bank cards
        "apps.customers": {
            "handlers": ["console", "app_file", "security_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },

        # Trading core — buy, sell, wallet
        "apps.exchange": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },

        # Payments and gateway
        "apps.payments": {
            "handlers": ["console", "app_file", "security_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },

        # Settlement and withdrawals
        "apps.settlements": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },

        # Celery tasks
        "apps.exchange.tasks": {
            "handlers": ["console", "celery_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.payments.tasks": {
            "handlers": ["console", "celery_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.settlements.tasks": {
            "handlers": ["console", "celery_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        
        # Django itself
        "django": {
            "handlers": ["console", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },

    # root logger — fallback for everything else
    "root": {
        "handlers": ["console", "error_file"],
        "level": "WARNING",
    },
}
