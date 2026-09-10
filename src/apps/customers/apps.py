from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.customers"

    label = "customers"

    def ready(self):
        # Imported for its side effect: registering the @receiver hooks.
        # noqa keeps `ruff check --fix` from deleting it as an unused
        # import, which silently unregisters every signal in this app.
        import apps.customers.signals.customer_signals  # noqa: F401
