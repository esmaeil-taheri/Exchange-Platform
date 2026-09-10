from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.notifications"

    label = "notifications"

    def ready(self):
        # Imported for its side effect: registering the @receiver hooks.
        # noqa keeps `ruff check --fix` from deleting it as an unused
        # import, which silently unregisters every signal in this app.
        import apps.notifications.signals.notification_signals  # noqa: F401
