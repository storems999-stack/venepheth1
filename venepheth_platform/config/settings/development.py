"""
Development settings — extends base.py.
Never use in production.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "testserver", ".trycloudflare.com"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://*.trycloudflare.com",
]
ACCOUNT_EMAIL_VERIFICATION = "none"

# ─── Database (SQLite for local dev without Docker) ───────────────────────────
import os
if not os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cache (LocMem if Redis not running) ─────────────────────────────────────
import os
if not os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Debug Toolbar ────────────────────────────────────────────────────────────
# INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# DEBUG_TOOLBAR_CONFIG = {
#     "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
# }

# ─── Relaxed Security for Development ────────────────────────────────────────
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# ─── Django Axes — Relaxed for Development ────────────────────────────────────
AXES_ENABLED = False

# ─── Celery — Eager mode so tasks run synchronously in dev ───────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ─── Logging ─────────────────────────────────────────────────────────────────
import logging
for handler in LOGGING["handlers"].values():  # noqa: F405
    if handler.get("class") == "logging.handlers.RotatingFileHandler":
        import os
        os.makedirs(BASE_DIR / "logs", exist_ok=True)  # noqa: F405
