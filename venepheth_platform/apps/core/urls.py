"""Core URL configuration."""

from django.urls import path

from . import views
from .legal_views import privacy_policy, terms_of_use
from .metrics import metrics_view

app_name = "core"

urlpatterns = [
    path("", views.homepage, name="home"),
    path("health/", views.health_check, name="health"),
    path("ready/", views.readiness_check, name="ready"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("metrics/", metrics_view, name="metrics"),
    path("503/", views.error_503, name="error_503"),
    # ── Legal pages (vision §45) ──────────────────────────────────────────────
    path("privacy/", privacy_policy, name="privacy"),
    path("terms/", terms_of_use, name="terms"),
]
