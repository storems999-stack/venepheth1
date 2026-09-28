"""
Core views — homepage, health check, custom error pages, rate limit handler.
"""

import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

logger = logging.getLogger("apps.core")


@require_GET
def homepage(request):
    """Public homepage."""
    from apps.blog.models import Article
    from apps.courses.models import Course
    from apps.profiles.models import Profile
    from apps.research.models import Publication, ResearchProject

    profile = Profile.objects.filter(is_active=True).first()

    courses_count = Course.objects.filter(status="published", visibility="public").count()
    publications_count = Publication.objects.filter(status="published").count()
    research_count = ResearchProject.objects.filter(status="published").count()

    context = {
        "profile": profile,
        "featured_courses": Course.objects.filter(
            status="published", visibility="public", featured=True
        ).select_related("category")[:6],
        "recent_research": ResearchProject.objects.filter(status="published").order_by("-updated_at")[:4],
        "recent_articles": Article.objects.filter(status=Article.Status.PUBLISHED).prefetch_related("tags")[:3],
        "recent_publications": Publication.objects.filter(status="published").order_by("-year")[:4],
        "stats": {
            "courses_count": courses_count,
            "publications_count": publications_count,
            "research_count": research_count,
        },
        "about_highlights": [
            {"icon": "book-open", "value": f"{courses_count}+", "label": "Courses Taught"},
            {"icon": "file-text", "value": f"{publications_count}+", "label": "Publications"},
            {"icon": "flask-conical", "value": f"{research_count}+", "label": "Research Projects"},
            {"icon": "users", "value": "500+", "label": "Students Taught"},
        ],
        "meta_title": settings.SITE_NAME,
        "meta_description": f"{settings.SITE_TAGLINE} — {settings.SITE_NAME}",
    }
    return render(request, "public/home.html", context)


@require_GET
def dashboard(request):
    """
    Lecturer Academic Studio & Management Dashboard (Vision §10 & §46).
    Restricted to authenticated staff/lecturer members.
    """
    if not request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect(f"{settings.LOGIN_URL}?next={request.path}")

    if not (request.user.is_staff or request.user.is_superuser):
        from django.shortcuts import redirect

        return redirect("core:home")

    from apps.analytics.models import PageView
    from apps.audit.models import AuditLog
    from apps.blog.models import Article
    from apps.contact.models import ContactMessage
    from apps.courses.models import Course
    from apps.profiles.models import Profile
    from apps.research.models import Publication, ResearchProject
    from apps.resources.models import Resource
    from apps.security.models import SecurityEvent

    profile = Profile.objects.filter(is_active=True).first()

    # Core Stats
    courses_published = Course.objects.filter(status="published").count()
    courses_draft = Course.objects.filter(status="draft").count()
    courses_total = courses_published + courses_draft

    research_ongoing = ResearchProject.objects.filter(research_status="ongoing").count()
    research_completed = ResearchProject.objects.filter(research_status__in=["completed", "published"]).count()
    research_total = ResearchProject.objects.count()

    publications_count = Publication.objects.count()

    articles_published = Article.objects.filter(status=Article.Status.PUBLISHED).count()
    articles_draft = Article.objects.filter(status=Article.Status.DRAFT).count()
    articles_total = Article.objects.count()

    resources_count = Resource.objects.count()

    unread_messages_count = ContactMessage.objects.filter(status=ContactMessage.Status.NEW).count()
    total_page_views = PageView.objects.count()

    # Publishing pipeline / Draft items
    draft_articles = Article.objects.filter(status=Article.Status.DRAFT).order_by("-updated_at")[:5]
    draft_courses = Course.objects.filter(status="draft").order_by("-updated_at")[:5]
    recent_inquiries = ContactMessage.objects.order_by("-created_at")[:5]

    # Recent Audit Log feed
    recent_audit_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:10]

    # Recent Security Events
    recent_security_events = SecurityEvent.objects.order_by("-timestamp")[:6]

    # System Health check
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    cache_ok = True
    try:
        from django.core.cache import cache

        cache.set("dashboard_ping", "ok", 5)
        cache_ok = cache.get("dashboard_ping") == "ok"
    except Exception:
        cache_ok = False

    context = {
        "profile": profile,
        "stats": {
            "courses_total": courses_total,
            "courses_published": courses_published,
            "courses_draft": courses_draft,
            "research_total": research_total,
            "research_ongoing": research_ongoing,
            "research_completed": research_completed,
            "publications_count": publications_count,
            "articles_total": articles_total,
            "articles_published": articles_published,
            "articles_draft": articles_draft,
            "resources_count": resources_count,
            "unread_messages_count": unread_messages_count,
            "total_page_views": total_page_views,
        },
        "draft_articles": draft_articles,
        "draft_courses": draft_courses,
        "recent_inquiries": recent_inquiries,
        "recent_audit_logs": recent_audit_logs,
        "recent_security_events": recent_security_events,
        "system_status": {
            "database": db_ok,
            "cache": cache_ok,
        },
        "meta_title": f"Academic Studio Dashboard — {settings.SITE_NAME}",
    }
    return render(request, "dashboard/index.html", context)


@require_GET
def health_check(request):
    """
    Health check endpoint for Docker/load balancer.
    Returns 200 if DB and cache are reachable, 503 otherwise.
    """
    checks = {}
    status = 200

    # DB check
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception:
        logger.warning("Health check: database unreachable", exc_info=True)
        checks["database"] = "error"
        status = 503

    # Cache check
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", 5)
        val = cache.get("health_check")
        checks["cache"] = "ok" if val == "ok" else "error"
    except Exception:
        logger.warning("Health check: cache unreachable", exc_info=True)
        checks["cache"] = "error"
        status = 503

    return JsonResponse({"status": "ok" if status == 200 else "error", "checks": checks}, status=status)


@require_GET
def readiness_check(request):
    """Kubernetes readiness probe (verifies the database is reachable)."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "not ready"}, status=503)
    return JsonResponse({"status": "ready"})


# ─── Custom Error Pages ────────────────────────────────────────────────────────
def error_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_429(request, exception=None):
    return render(request, "errors/429.html", status=429)


def error_500(request):
    return render(request, "errors/500.html", status=500)


def error_503(request, exception=None):
    return render(request, "errors/503.html", status=503)


def rate_limited(request, exception=None):
    """Called by django-ratelimit when a rate limit is exceeded."""
    return JsonResponse(
        {"error": "Too many requests. Please try again later."},
        status=429,
    )
