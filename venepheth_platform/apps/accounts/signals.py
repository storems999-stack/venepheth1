"""
Signals for the accounts app:
- Audit log on login/logout/failure
- Auto-require MFA for admin roles
"""

import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.accounts.models import CustomUser

logger = logging.getLogger("apps.audit")


def get_client_ip(request):
    if request is None:
        return None
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    logger.info("LOGIN_SUCCESS user=%s ip=%s", user.email, ip)
    # Update last_login_ip
    CustomUser.objects.filter(pk=user.pk).update(last_login_ip=ip)
    # Create audit log entry
    try:
        from apps.audit.models import AuditLog

        AuditLog.log(
            who=user,
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.SUCCESS,
            ip=ip,
            request=request,
        )
    except Exception:
        pass


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user:
        ip = get_client_ip(request)
        logger.info("LOGOUT user=%s ip=%s", user.email, ip)
        try:
            from apps.audit.models import AuditLog

            AuditLog.log(
                who=user,
                action=AuditLog.Action.LOGOUT,
                result=AuditLog.Result.SUCCESS,
                ip=ip,
                request=request,
            )
        except Exception:
            pass


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    email = credentials.get("email", credentials.get("username", "unknown"))
    logger.warning("LOGIN_FAILED email=%s ip=%s", email, ip)
    try:
        from apps.security.models import SecurityEvent

        SecurityEvent.record(
            event_type=SecurityEvent.EventType.LOGIN_FAILURE,
            description=f"Failed login attempt for: {email}",
            ip=ip,
            request=request,
        )
    except Exception:
        pass


@receiver(post_save, sender=CustomUser)
def enforce_mfa_for_admins(sender, instance, created, **kwargs):
    """Auto-set require_mfa=True for ADMIN/SUPERADMIN roles (including promotions)."""
    if instance.role in (CustomUser.Role.SUPERADMIN, CustomUser.Role.ADMIN) and not instance.require_mfa:
        # Queryset update: no signal recursion.
        CustomUser.objects.filter(pk=instance.pk, require_mfa=False).update(require_mfa=True)


try:
    from allauth.account.signals import password_changed as allauth_password_changed
except ImportError:  # pragma: no cover — allauth always installed here
    allauth_password_changed = None


if allauth_password_changed is not None:

    @receiver(allauth_password_changed)
    def clear_forced_password_change(sender, request, user, **kwargs):
        """A successful password change satisfies must_change_password."""
        CustomUser.objects.filter(pk=user.pk).update(must_change_password=False, password_changed_at=timezone.now())
