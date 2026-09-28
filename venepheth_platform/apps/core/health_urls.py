"""
Health check URL patterns (vision §43).
Included at /health/ from config/urls.py

  GET /health/       — Liveness + dependency check (DB, cache)
  GET /health/ready/ — Readiness probe
  GET /health/live/  — Simple liveness probe (no dep check)
"""

from django.http import JsonResponse
from django.urls import path

from apps.core.views import health_check, readiness_check


def liveness(request):
    """Simple liveness probe — returns 200 if Django is running."""
    return JsonResponse({"status": "alive"})


urlpatterns = [
    path("", health_check, name="health"),
    path("ready/", readiness_check, name="health-ready"),
    path("live/", liveness, name="health-live"),
]
