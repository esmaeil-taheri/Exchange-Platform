from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.accounts"

    label = "accounts"

    def ready(self):
        # Imported for its side effect: registering the @receiver hooks.
        # noqa keeps `ruff check --fix` from deleting it as an unused
        # import, which silently unregisters every signal in this app.
        import apps.accounts.signals.user_signals  # noqa: F401
