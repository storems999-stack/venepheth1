"""
Analytics middleware.
"""

import logging
from urllib.parse import urlsplit, urlunsplit

from apps.analytics.models import PageView
from apps.core.utils import get_client_ip

logger = logging.getLogger("apps.analytics")

SKIP_PATHS = [
    "/accounts/",
    "/health",
    "/ready/",
    "/live/",
    "/metrics/",
    "/sitemap.xml",
    "/robots.txt",
    "/static/",
    "/media/",
    "/__debug__/",
    "/admin/",
    "/secure-admin/",
    "/api/",
]


def _safe_referer(value):
    """Store only a valid HTTP(S) origin; referrer paths and params may carry tokens."""
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return ""

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not hostname:
        return ""

    host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = f"{host}:{port}" if port is not None else host
    return urlunsplit((scheme, netloc, "", "", ""))


class PageViewMiddleware:
    """Records page views for analytics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._maybe_log(request, response)
        return response

    def _maybe_log(self, request, response):
        if request.method != "GET":
            return

        path = request.path
        if any(path == skip.rstrip("/") or path.startswith(skip) for skip in SKIP_PATHS):
            return

        try:
            PageView.objects.create(
                path=path,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
                referer=_safe_referer(request.META.get("HTTP_REFERER", "")),
                is_authenticated=request.user.is_authenticated if hasattr(request, "user") else False,
            )
        except Exception as e:
            logger.error("Failed to record page view: %s", e)
