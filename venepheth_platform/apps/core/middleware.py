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


def client_ip_from_forwarded(peer_ip: str, forwarded: str | None) -> str:
    """Resolve the nearest untrusted hop in a trusted proxy's XFF chain."""
    if not peer_ip or not peer_is_trusted(peer_ip) or not forwarded:
        return peer_ip

    for candidate in reversed(forwarded.split(",")):
        candidate = candidate.strip()
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if not peer_is_trusted(candidate):
            return candidate
    return peer_ip


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
        real_ip = client_ip_from_forwarded(peer_ip, request.META.get("HTTP_X_FORWARDED_FOR"))
        if real_ip and real_ip != peer_ip:
            request.META["REMOTE_ADDR"] = real_ip
        return self.get_response(request)
