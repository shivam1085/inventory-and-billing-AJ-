from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Register system checks
        from . import checks  # noqa: F401
        # Register signals (e.g., Firebase logging)
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Signals are optional and should never block app startup
            pass
