"""
Development settings — extends base.py.
Never use in production.
"""

import os

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "testserver", ".trycloudflare.com", ".workers.dev"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:9000",
    "http://127.0.0.1:9000",
    "https://*.trycloudflare.com",
    "https://*.workers.dev",
]
ACCOUNT_EMAIL_VERIFICATION = "none"

# ─── Database (SQLite for local dev without Docker) ───────────────────────────
if not os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cache (LocMem if Redis not running) ─────────────────────────────────────
if not os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Debug Toolbar ────────────────────────────────────────────────────────────
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
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
for handler in LOGGING["handlers"].values():
    if handler.get("class") == "logging.handlers.RotatingFileHandler":
        import os

        os.makedirs(BASE_DIR / "logs", exist_ok=True)
