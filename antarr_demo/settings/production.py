import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

# Optional 12-factor configuration. settings/local.py (gitignored) overrides these.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(",") if host.strip()]

try:
    from .local import *
except ImportError:
    pass

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY or define SECRET_KEY in settings/local.py"
    )

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Set DJANGO_ALLOWED_HOSTS or define ALLOWED_HOSTS in settings/local.py"
    )
