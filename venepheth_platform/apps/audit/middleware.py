"""
Audit middleware — auto-logs POST/PUT/PATCH/DELETE requests by authenticated users.
"""

import logging

logger = logging.getLogger("apps.audit")

SENSITIVE_PATHS = ["/accounts/login/", "/accounts/password/"]
SKIP_PATHS = ["/health/", "/ready/", "/static/", "/media/", "/__debug__/"]


class AuditMiddleware:
    """
    Middleware that logs sensitive actions automatically.
    Only logs state-changing requests (POST, PUT, PATCH, DELETE).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._maybe_log(request, response)
        return response

    def _maybe_log(self, request, response):
        # Only log state-changing methods
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        # Skip health checks and static
        if any(request.path.startswith(skip) for skip in SKIP_PATHS):
            return
        # Only log authenticated users
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return
        # Skip sensitive endpoints (they have their own audit hooks)
        if any(request.path.startswith(sensitive) for sensitive in SENSITIVE_PATHS):
            return

        try:
            from apps.audit.models import AuditLog

            action = {
                "POST": AuditLog.Action.CREATE,
                "PUT": AuditLog.Action.UPDATE,
                "PATCH": AuditLog.Action.UPDATE,
                "DELETE": AuditLog.Action.DELETE,
            }.get(request.method, AuditLog.Action.UPDATE)

            result = AuditLog.Result.SUCCESS if 200 <= response.status_code < 400 else AuditLog.Result.FAILURE

            AuditLog.log(
                who=request.user,
                action=action,
                result=result,
                request=request,
                description=f"{request.method} {request.path} → {response.status_code}",
            )
        except Exception as e:
            logger.error("AuditMiddleware error: %s", e)
