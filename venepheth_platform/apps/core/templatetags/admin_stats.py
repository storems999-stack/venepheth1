"""Template tags for the custom Django admin dashboard (templates/admin/index.html).

The admin index template expects a ``dashboard_stats`` mapping plus recent
activity feeds. The default ``AdminSite`` provides neither, so this tag
computes them defensively — the admin must never 500 because of a widget.
"""

import logging

from django import template

register = template.Library()
logger = logging.getLogger("apps.core")


@register.simple_tag
def admin_dashboard():
    """Return live counts + recent feeds for the admin dashboard."""
    stats = {
        "courses": 0,
        "publications": 0,
        "students": 0,
        "security_events": 0,
    }
    recent_logs = []
    critical_events = []
    try:
        from apps.accounts.models import CustomUser
        from apps.audit.models import AuditLog
        from apps.courses.models import Course
        from apps.research.models import Publication
        from apps.security.models import SecurityEvent

        stats["courses"] = Course.objects.count()
        stats["publications"] = Publication.objects.count()
        stats["students"] = CustomUser.objects.filter(role=CustomUser.Role.STUDENT, is_active=True).count()
        stats["security_events"] = SecurityEvent.objects.filter(resolved=False).count()
        recent_logs = list(AuditLog.objects.select_related("user").order_by("-timestamp")[:10])
        critical_events = list(
            SecurityEvent.objects.filter(
                severity__in=[
                    SecurityEvent.Severity.HIGH,
                    SecurityEvent.Severity.CRITICAL,
                ],
                resolved=False,
            ).order_by("-timestamp")[:5]
        )
    except Exception:
        logger.exception("admin_dashboard tag failed; rendering zeros")
    return {
        "stats": stats,
        "recent_logs": recent_logs,
        "critical_events": critical_events,
    }
