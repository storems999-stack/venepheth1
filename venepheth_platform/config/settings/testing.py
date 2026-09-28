"""
Testing settings — fast, in-memory database, no migrations.
"""

from .base import *

DEBUG = True

import importlib.util


def _is_available(entry):
    root = entry.split(".")[0]
    try:
        return importlib.util.find_spec(root) is not None
    except Exception:
        return False


INSTALLED_APPS = [app for app in INSTALLED_APPS if _is_available(app)]
MIDDLEWARE = [m for m in MIDDLEWARE if _is_available(m)]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Skip migrations for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable axes during tests
AXES_ENABLED = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",  # Fast hashing for tests
]

LOGGING = {"version": 1, "disable_existing_loggers": True}

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
