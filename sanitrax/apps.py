from django.apps import AppConfig


class SanitraxConfig(AppConfig):
    name = 'sanitrax'

    def ready(self):
        # Branche les récepteurs du journal de connexion
        from . import signals  # noqa: F401
