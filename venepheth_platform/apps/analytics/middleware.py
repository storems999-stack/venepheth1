"""
Analytics middleware.
"""

import logging

from apps.analytics.models import PageView
from apps.core.utils import get_client_ip

logger = logging.getLogger("apps.analytics")

SKIP_PATHS = [
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
                referer=request.META.get("HTTP_REFERER", "")[:512],
                is_authenticated=request.user.is_authenticated if hasattr(request, "user") else False,
            )
        except Exception as e:
            logger.error("Failed to record page view: %s", e)
