"""Shared core utilities."""

from apps.core.middleware import client_ip_from_forwarded


def get_client_ip(request):
    """Return the client IP address.

    ``X-Forwarded-For`` is attacker-controlled: any client can send it. It is
    honoured only when the direct peer (REMOTE_ADDR) is a configured trusted
    proxy, i.e. the same allowlist check TrustedProxyMiddleware applies. The
    check is repeated here rather than relying on middleware ordering, so this
    stays correct even if the middleware stack is reordered.

    Do NOT read HTTP_X_FORWARDED_FOR directly anywhere else. Beyond forging
    AuditLog / SecurityEvent / PageView / last_login_ip, a garbage value makes
    the INSERT fail on PostgreSQL's ``inet`` column; callers that swallow that
    error (AuditMiddleware) then lose the audit row entirely while still
    returning HTTP 200.
    """
    if request is None:
        return None
    meta = getattr(request, "META", None) or {}
    peer = meta.get("REMOTE_ADDR")
    return client_ip_from_forwarded(peer, meta.get("HTTP_X_FORWARDED_FOR"))
