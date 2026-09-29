"""Core middleware — trusted proxy handling."""

import ipaddress
import logging

from django.conf import settings

logger = logging.getLogger("apps.core")


def peer_is_trusted(peer_ip: str) -> bool:
    """True when the direct peer matches TRUSTED_PROXY_IPS (IPs or CIDRs)."""
    for entry in getattr(settings, "TRUSTED_PROXY_IPS", []):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if ipaddress.ip_address(peer_ip) in ipaddress.ip_network(entry, strict=False):
                    return True
            elif peer_ip == entry:
                return True
        except ValueError:
            continue
    return False


# Backwards-compatible private alias.
_peer_is_trusted = peer_is_trusted


class TrustedProxyMiddleware:
    """
    Set REMOTE_ADDR from X-Forwarded-For when the direct peer is trusted.

    Must run first so rate limiting (django-ratelimit, axes) and audit logs
    see the real client IP instead of the proxy's. With an empty
    TRUSTED_PROXY_IPS (default), proxy headers are never trusted.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        peer_ip = request.META.get("REMOTE_ADDR")
        if peer_ip and peer_is_trusted(peer_ip):
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            if forwarded:
                real_ip = forwarded.split(",")[0].strip()
                if real_ip:
                    request.META["REMOTE_ADDR"] = real_ip
        return self.get_response(request)
