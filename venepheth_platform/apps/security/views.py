"""Security views — lockout response for django-axes."""

import logging

from django.http import HttpResponse

from .models import SecurityEvent

logger = logging.getLogger("apps.security")


def lockout_response(request, credentials, *args, **kwargs):
    """Called by django-axes when an account is locked out."""
    try:
        username = str(credentials.get("username", "unknown"))
        username = username.replace("\n", " ").replace("\r", " ")[:150]
        SecurityEvent.record(
            event_type=SecurityEvent.EventType.ACCOUNT_LOCKED,
            description=f"Account locked for: {username}",
            request=request,
            severity=SecurityEvent.Severity.HIGH,
        )
    except Exception:
        logger.exception("Failed to record account lockout event")
    return HttpResponse(
        "<h1>Too many failed attempts. Your access has been temporarily blocked.</h1>",
        status=403,
    )
