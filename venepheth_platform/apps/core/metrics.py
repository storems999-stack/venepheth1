"""
Prometheus-compatible /metrics/ endpoint.
Zero-cost observability — no external agent required.
Metrics are exposed in Prometheus text format (exposition format 0.0.4).
"""

import logging
import time

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("apps.core")

User = get_user_model()

# Start-time for uptime metric
_START_TIME = time.time()


def _safe_count(queryset) -> int:
    try:
        return queryset.count()
    except Exception:
        logger.exception("Failed to collect a database-backed platform metric")
        return -1


def _safe_import_count(app: str, model: str, **filters) -> int:
    try:
        import importlib

        mod = importlib.import_module(f"apps.{app}.models")
        klass = getattr(mod, model, None)
        if klass is None:
            return -1
        return klass.objects.filter(**filters).count()
    except Exception:
        logger.exception("Failed to collect an imported platform metric: %s.%s", app, model)
        return -1


@require_GET
def metrics_view(request):
    """
    Prometheus metrics endpoint at /metrics/.
    Protect this endpoint behind IP allowlist or HTTP basic auth in nginx.
    """
    # Validate optional shared secret
    from django.conf import settings

    metrics_token = getattr(settings, "METRICS_TOKEN", None)
    if metrics_token:
        auth_header = request.META.get("HTTP_X_METRICS_TOKEN", "")
        if auth_header != metrics_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain")
    elif getattr(settings, "METRICS_REQUIRE_TOKEN", False):
        # Fail-closed where required (production): unset token must not expose metrics.
        return HttpResponse("Forbidden", status=403, content_type="text/plain")

    now = time.time()
    uptime = now - _START_TIME

    lines = [
        "# HELP platform_uptime_seconds Time since process start in seconds.",
        "# TYPE platform_uptime_seconds gauge",
        f"platform_uptime_seconds {uptime:.1f}",
        # ── Users ──────────────────────────────────────────────────────────────
        "# HELP platform_users_total Total registered users.",
        "# TYPE platform_users_total gauge",
        f"platform_users_total {_safe_count(User.objects.all())}",
        "# HELP platform_active_users_total Active (is_active=True) users.",
        "# TYPE platform_active_users_total gauge",
        f"platform_active_users_total {_safe_count(User.objects.filter(is_active=True))}",
        # ── Blog ───────────────────────────────────────────────────────────────
        "# HELP platform_articles_total Published blog articles.",
        "# TYPE platform_articles_total gauge",
        f"platform_articles_total {_safe_import_count('blog', 'Article', status='published')}",
        # ── Research ───────────────────────────────────────────────────────────
        "# HELP platform_research_projects_total Active research projects.",
        "# TYPE platform_research_projects_total gauge",
        f"platform_research_projects_total {_safe_import_count('research', 'ResearchProject', status='published')}",
        # ── Publications ────────────────────────────────────────────────────────
        "# HELP platform_publications_total Total publications.",
        "# TYPE platform_publications_total gauge",
        f"platform_publications_total {_safe_import_count('research', 'Publication')}",
        # ── Courses ─────────────────────────────────────────────────────────────
        "# HELP platform_courses_total Active courses.",
        "# TYPE platform_courses_total gauge",
        f"platform_courses_total {_safe_import_count('courses', 'Course', status='published')}",
        # ── Timestamp ──────────────────────────────────────────────────────────
        "# HELP platform_scrape_timestamp_seconds Unix timestamp of last metric scrape.",
        "# TYPE platform_scrape_timestamp_seconds gauge",
        f"platform_scrape_timestamp_seconds {now:.0f}",
    ]

    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")
