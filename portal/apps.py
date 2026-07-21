from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal"
    verbose_name = "Senhorios portal"

    def ready(self):
        from portal import signals  # noqa: F401
