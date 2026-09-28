"""
Audit Log model — records WHO did WHAT, WHEN, WHERE, with what RESULT.

IMPORTANT: Never store passwords, tokens, or secrets in audit logs.
"""

import logging

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("apps.audit")


class AuditLog(models.Model):
    """
    Immutable audit trail for all significant actions in the system.
    Records are never deleted or modified — only new records are added.
    """

    class Action(models.TextChoices):
        # Auth
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        LOGIN_FAILED = "login_failed", _("Login Failed")
        PASSWORD_CHANGE = "password_change", _("Password Change")
        MFA_SETUP = "mfa_setup", _("MFA Setup")
        MFA_VERIFIED = "mfa_verified", _("MFA Verified")

        # Content
        CREATE = "create", _("Create")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")
        PUBLISH = "publish", _("Publish")
        UNPUBLISH = "unpublish", _("Unpublish")
        ARCHIVE = "archive", _("Archive")
        RESTORE = "restore", _("Restore")

        # Admin
        USER_CREATED = "user_created", _("User Created")
        USER_ACTIVATED = "user_activated", _("User Activated")
        USER_DEACTIVATED = "user_deactivated", _("User Deactivated")
        ROLE_CHANGED = "role_changed", _("Role Changed")
        PERMISSION_CHANGED = "permission_changed", _("Permission Changed")

        # File
        FILE_UPLOAD = "file_upload", _("File Upload")
        FILE_DOWNLOAD = "file_download", _("File Download")
        FILE_DELETE = "file_delete", _("File Delete")

        # Security
        ACCOUNT_LOCKED = "account_locked", _("Account Locked")
        IP_BLOCKED = "ip_blocked", _("IP Blocked")

    class Result(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILURE = "failure", _("Failure")
        ERROR = "error", _("Error")

    # ─── Who ────────────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("user"),
    )
    user_email = models.EmailField(
        _("user email"),
        blank=True,
        default="",
        help_text=_("Snapshot of user email at time of action."),
    )

    # ─── What ───────────────────────────────────────────────────────────────────
    action = models.CharField(_("action"), max_length=50, choices=Action.choices, db_index=True)
    description = models.TextField(_("description"), blank=True, default="")

    # ─── Object ─────────────────────────────────────────────────────────────────
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("content type"),
    )
    object_id = models.CharField(_("object ID"), max_length=255, blank=True, default="")
    object_repr = models.CharField(
        _("object representation"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("String representation of the affected object at time of action."),
    )

    # ─── When ───────────────────────────────────────────────────────────────────
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now, db_index=True)

    # ─── Where ──────────────────────────────────────────────────────────────────
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True, default="")
    request_path = models.CharField(_("request path"), max_length=255, blank=True, default="")
    request_method = models.CharField(_("request method"), max_length=10, blank=True, default="")

    # ─── Result ─────────────────────────────────────────────────────────────────
    result = models.CharField(
        _("result"),
        max_length=20,
        choices=Result.choices,
        default=Result.SUCCESS,
        db_index=True,
    )
    extra_data = models.JSONField(_("extra data"), default=dict, blank=True)

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user_email} | {self.action} | {self.result} | {self.timestamp:%Y-%m-%d %H:%M:%S}"

    @classmethod
    def log(cls, who, action, result=Result.SUCCESS, ip=None, request=None, obj=None, description="", extra=None):
        """
        Convenience method to create an audit log entry.

        Usage:
            AuditLog.log(who=user, action=AuditLog.Action.UPDATE, obj=course)
        """
        from django.contrib.contenttypes.models import ContentType

        entry = cls(
            user=who,
            user_email=getattr(who, "email", "") if who else "",
            action=action,
            result=result,
            description=description,
            extra_data=extra or {},
            request_method="",
            request_path="",
            user_agent="",
            object_id="",
            object_repr="",
        )

        if ip:
            entry.ip_address = ip
        elif request and hasattr(request, "META"):
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            entry.ip_address = x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")

        if request:
            if hasattr(request, "META"):
                entry.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512]
            entry.request_path = (getattr(request, "path", "") or "")[:255]
            entry.request_method = getattr(request, "method", "") or ""

        if obj:
            try:
                entry.content_type = ContentType.objects.get_for_model(obj)
                entry.object_id = str(obj.pk)
                entry.object_repr = str(obj)[:255]
            except Exception:
                pass

        entry.save()
        logger.info("AUDIT %s | %s | %s | %s", who, action, result, entry.ip_address)
        return entry
