"""
Base settings for Venepheth SAYAVONG Academic Platform.
All environments inherit from this file.
"""

from pathlib import Path

import environ

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Environment ──────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ─── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
# Obscured admin path (e.g. ADMIN_URL=secure-admin/). Empty/default = admin/.
ADMIN_URL = env("ADMIN_URL", default="admin/")

# ─── Application Definition ───────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    # REST API
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    # Auth
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "axes",
    # Content
    "simple_history",
    "django_cleanup.apps.CleanupConfig",
    # UI
    "django_htmx",
    "widget_tweaks",
    # Celery
    "django_celery_beat",
    "django_celery_results",
    # Extensions
    "django_extensions",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.profiles.apps.ProfilesConfig",
    "apps.courses.apps.CoursesConfig",
    "apps.teaching.apps.TeachingConfig",
    "apps.research.apps.ResearchConfig",
    "apps.publications.apps.PublicationsConfig",
    "apps.resources.apps.ResourcesConfig",
    "apps.blog.apps.BlogConfig",
    "apps.contact.apps.ContactConfig",
    "apps.search.apps.SearchConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.security.apps.SecurityConfig",
    "apps.assistant.apps.AssistantConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "apps.core.middleware.TrustedProxyMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.UserPreferenceMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.accounts.middleware.SecurityEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "axes.middleware.AxesMiddleware",
    "apps.audit.middleware.AuditMiddleware",
    "apps.analytics.middleware.PageViewMiddleware",
]

ROOT_URLCONF = "config.urls"

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
# connect_timeout is a libpq/psycopg option. Passing it to the sqlite3 backend
# raises "Connection() got an unexpected keyword argument 'connect_timeout'",
# which takes down any run configured with a SQLite DATABASE_URL — including
# base.py's own default when it is exported into the environment.
if "postgresql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10}

# ─── Cache & Queue ────────────────────────────────────────────────────────────
# REDIS_URL wins when set. Otherwise compose it from REDIS_PASSWORD: a plain
# `redis://redis:6379/0` against a server started with --requirepass makes every
# cache write and Celery connection fail, and the worker/scheduler crash-loop.
REDIS_PASSWORD = env("REDIS_PASSWORD", default="")
REDIS_URL = env("REDIS_URL", default="") or (
    f"redis://:{REDIS_PASSWORD}@redis:6379/0" if REDIS_PASSWORD else "redis://redis:6379/0"
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# ─── Authentication ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Password Reset ────────────────────────────────────────────────────────────
# Reset links expire after 24h (Django default is 3 days).
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

# ─── Session Security ─────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 3600 * 8  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("lo", "ພາສາລາວ"),
]
TIME_ZONE = "Asia/Vientiane"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# ─── Static & Media Files ─────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Default Primary Key ──────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@venepheth.edu.la")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ─── Celery ───────────────────────────────────────────────────────────────────
# Reuse the resolved REDIS_URL above so the broker carries the password too.
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# ─── Django Axes (Brute-force Protection) ────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_RESET_ON_SUCCESS = True

# ─── Content Security Policy (enforcing, nonce-free by design) ─────────────────
# All first-party JS lives in static/js/*.js so cached pages (blog/research/
# courses lists) share byte-identical HTML — per-request nonces would break
# on cache hits (stale nonce in HTML vs fresh nonce in header). Inline event
# handlers are banned — UI actions go through the delegated listener in
# static/js/site.js ([data-print], [data-reload], [data-copy],
# form[data-confirm]). The two remaining nonced snippets (cv_print page,
# parked assistant templates) sit on uncached views.
# - style-src keeps 'unsafe-inline': required by the Tailwind Play CDN,
#   which injects generated styles, and by style="" attributes.
# - EXCLUDE_URL_PREFIXES: Django admin and DRF/Swagger ship extensive
#   first-party inline scripts; sandboxing them is a separate project.
from csp.constants import SELF as _CSP_SELF

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [_CSP_SELF],
        "script-src": [
            _CSP_SELF,
            "https://cdn.tailwindcss.com",
            "https://unpkg.com",
        ],
        "style-src": [
            _CSP_SELF,
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
        ],
        "font-src": [_CSP_SELF, "https://fonts.gstatic.com", "data:"],
        "img-src": [_CSP_SELF, "data:", "https:"],
        "connect-src": [_CSP_SELF],
        "frame-ancestors": ["'none'"],
        "form-action": [_CSP_SELF],
        "base-uri": [_CSP_SELF],
        "object-src": ["'none'"],
    },
    # Derive the admin prefix from ADMIN_URL instead of hardcoding
    # "/secure-admin/": that value is configurable, and a mismatch would leave
    # the admin under the enforced policy — its own index page sets
    # `tailwind.config` in an inline script and would silently stop rendering.
    "EXCLUDE_URL_PREFIXES": ["/api/", "/" + ADMIN_URL.lstrip("/")],
}

# ─── Django Allauth ───────────────────────────────────────────────────────────
# Public registration CLOSED — admins create accounts (see apps/accounts/adapter.py).
ACCOUNT_ADAPTER = "apps.accounts.adapter.ClosedSignupAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
# NOTE: password1 must stay in SIGNUP_FIELDS — allauth deletes the login
# password field when it's absent (_setup_password_field), which silently
# breaks /accounts/login/ (renders name="" so no password is posted).
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Do NOT set ACCOUNT_AUTHENTICATION_METHOD / ACCOUNT_USERNAME_REQUIRED /
# ACCOUNT_EMAIL_REQUIRED. allauth 65.19 deprecates all three and derives them
# from ACCOUNT_LOGIN_METHODS + ACCOUNT_SIGNUP_FIELDS above, which already
# declare email-only auth with no username. (On allauth 65.3 the old settings
# were required or startup raised SystemCheckError; target the pinned version.)
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_RATE_LIMITS = {"login_failed": "5/300s"}
ACCOUNT_MFA_ENABLED = True
ACCOUNT_MFA_TOTP_ENABLED = True
ACCOUNT_MFA_RECOVERY_CODES_ENABLED = True
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000", "http://127.0.0.1:8000"])

# ─── File Upload Security ─────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB in memory threshold
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB total

ALLOWED_UPLOAD_EXTENSIONS = {
    "document": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".md"],
    # NOTE: ".svg" deliberately excluded — SVGs served from /media/ execute
    # inline JavaScript (stored XSS). Use PNG/WebP for vector-like graphics.
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "video": [".mp4", ".webm", ".mov"],
    "archive": [".zip"],
}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

# ─── Trusted Proxies ─────────────────────────────────────────────────────────
# IPs/CIDRs allowed to set X-Forwarded-For (nginx, load balancer).
# Empty = never trust proxy headers. REMOTE_ADDR is used directly then.
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=[])

# ─── Rate Limiting ─────────────────────────────────────────────────
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = "apps.core.views.rate_limited"
RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = False  # Fail closed: if Redis is down, block requests

# ─── Protected File Serving ────────────────────────────────────────────────
# True in production: Django answers download views with X-Accel-Redirect and
# nginx serves bytes from an `internal` location (direct /media/ URLs for
# resources/publications/course-files are denied in nginx.prod.conf).
SENDFILE_ENABLED = env.bool("SENDFILE_ENABLED", default=False)

# ─── Metrics ─────────────────────────────────────────────────────────
# Shared secret for /metrics/ (sent as X-Metrics-Token header by Prometheus).
# Empty = open endpoint (dev only). Production MUST set this.
METRICS_TOKEN = env("METRICS_TOKEN", default="")
# When True, /metrics/ returns 403 unless a valid token is presented.
METRICS_REQUIRE_TOKEN = env.bool("METRICS_REQUIRE_TOKEN", default=False)

# ─── AI Academic Assistant ──────────────────────────────────────────
# Google Gemini key for grounded answers. Empty = zero-cost local engine
# (GroundedFallbackAdapter). Get a key at https://aistudio.google.com/apikey
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

# ─── Simple History ─────────────────────────────────────────────────
SIMPLE_HISTORY_REVERT_DISABLED = False
SIMPLE_HISTORY_HISTORY_CHANGE_REASON_USE_TEXT_FIELD = True

# ─── API Spectacular ─────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Venepheth SAYAVONG Academic Platform API",
    "DESCRIPTION": "RESTful API for the academic management platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
}

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
        "apps.security": {"handlers": ["console", "security_file"], "level": "WARNING", "propagate": False},
        "apps.audit": {"handlers": ["console", "security_file"], "level": "INFO", "propagate": False},
        "axes": {"handlers": ["security_file"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}

# ─── Site Meta ────────────────────────────────────────────────────────────────
SITE_ID = 1
SITE_NAME = "Venepheth SAYAVONG Academic Platform"
SITE_TAGLINE = "Lecturer · Researcher · Academic"

# Google Analytics and Search Console
GOOGLE_ANALYTICS_ID = env.str("GOOGLE_ANALYTICS_ID", default="")
GOOGLE_SITE_VERIFICATION = env.str("GOOGLE_SITE_VERIFICATION", default="")
