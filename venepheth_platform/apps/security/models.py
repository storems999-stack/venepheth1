"""
Security events model — records anomalies, blocked attempts, and threats.
"""

import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("apps.security")


class SecurityEvent(models.Model):
    """Records security-relevant events for monitoring and alerting."""

    class EventType(models.TextChoices):
        LOGIN_FAILURE = "login_failure", _("Login Failure")
        ACCOUNT_LOCKED = "account_locked", _("Account Locked")
        IP_BLOCKED = "ip_blocked", _("IP Blocked")
        BRUTE_FORCE = "brute_force", _("Brute Force Detected")
        FILE_REJECTED = "file_rejected", _("File Upload Rejected")
        PERMISSION_DENIED = "permission_denied", _("Permission Denied")
        CSRF_FAILURE = "csrf_failure", _("CSRF Failure")
        RATE_LIMITED = "rate_limited", _("Rate Limited")
        SUSPICIOUS_ACTIVITY = "suspicious", _("Suspicious Activity")

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    event_type = models.CharField(_("event type"), max_length=50, choices=EventType.choices, db_index=True)
    severity = models.CharField(
        _("severity"), max_length=20, choices=Severity.choices, default=Severity.MEDIUM, db_index=True
    )
    description = models.TextField(_("description"))
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True, db_index=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    request_path = models.CharField(_("request path"), max_length=255, blank=True)
    extra_data = models.JSONField(_("extra data"), default=dict, blank=True)
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now, db_index=True)
    resolved = models.BooleanField(_("resolved"), default=False)
    resolved_at = models.DateTimeField(_("resolved at"), null=True, blank=True)

    class Meta:
        verbose_name = _("security event")
        verbose_name_plural = _("security events")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
            models.Index(fields=["severity", "resolved"]),
        ]

    def __str__(self):
        return f"{self.event_type} | {self.severity} | {self.ip_address} | {self.timestamp:%Y-%m-%d %H:%M}"

    @classmethod
    def record(cls, event_type, description, ip=None, request=None, severity=None, extra=None):
        """Create a security event record."""
        # Auto-assign severity based on event type
        severity_map = {
            cls.EventType.LOGIN_FAILURE: cls.Severity.MEDIUM,
            cls.EventType.BRUTE_FORCE: cls.Severity.HIGH,
            cls.EventType.ACCOUNT_LOCKED: cls.Severity.HIGH,
            cls.EventType.IP_BLOCKED: cls.Severity.HIGH,
            cls.EventType.CSRF_FAILURE: cls.Severity.HIGH,
            cls.EventType.FILE_REJECTED: cls.Severity.MEDIUM,
            cls.EventType.PERMISSION_DENIED: cls.Severity.LOW,
            cls.EventType.RATE_LIMITED: cls.Severity.MEDIUM,
            cls.EventType.SUSPICIOUS_ACTIVITY: cls.Severity.HIGH,
        }
        event = cls(
            event_type=event_type,
            severity=severity or severity_map.get(event_type, cls.Severity.MEDIUM),
            description=description,
            extra_data=extra or {},
        )
        if ip:
            event.ip_address = ip
        elif request:
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            event.ip_address = x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")
        if request:
            event.user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
            event.request_path = request.path[:255]
        event.save()
        logger.warning("SECURITY_EVENT %s | %s | %s", event_type, event.severity, event.ip_address)
        return event


def lockout_response(request, credentials, *args, **kwargs):
    """Called by django-axes when an account is locked out."""
    from django.http import HttpResponse

    SecurityEvent.record(
        event_type=SecurityEvent.EventType.ACCOUNT_LOCKED,
        description=f"Account locked for: {credentials.get('username', 'unknown')}",
        request=request,
        severity=SecurityEvent.Severity.HIGH,
    )
    return HttpResponse(
        "<h1>Too many failed attempts. Your access has been temporarily blocked.</h1>",
        status=403,
    )
