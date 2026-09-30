"""
Account views — login, logout, profile, password change, dashboard redirect.
Uses django-allauth for core auth flows; adds custom wrappers for audit logging.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.audit.models import AuditLog

from .models import CustomUser

logger = logging.getLogger("apps.accounts")


# ─── Profile / Account ────────────────────────────────────────────────────────


@login_required
def account_overview(request):
    """
    Authenticated user's account overview page.
    Shows profile info, MFA status, recent login activity.
    """
    from apps.audit.models import AuditLog

    recent_logins = AuditLog.objects.filter(
        user=request.user,
        action__in=[AuditLog.Action.LOGIN, AuditLog.Action.LOGIN_FAILED],
    ).order_by("-timestamp")[:10]

    context = {
        "recent_logins": recent_logins,
        "meta_title": _("My Account") + f" — {settings.SITE_NAME}",
    }
    return render(request, "account/overview.html", context)


@login_required
def profile_edit(request):
    """Edit basic profile fields (first name, last name, language, timezone)."""
    from .forms import ProfileUpdateForm

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            AuditLog.log(
                who=request.user,
                action=AuditLog.Action.UPDATE,
                obj=user,
                description="User updated their profile.",
                request=request,
            )
            messages.success(request, _("Profile updated successfully."))
            return redirect("accounts:overview")
    else:
        form = ProfileUpdateForm(instance=request.user)

    context = {
        "form": form,
        "meta_title": _("Edit Profile") + f" — {settings.SITE_NAME}",
    }
    return render(request, "account/profile_edit.html", context)


@login_required
def password_change_done(request):
    """Shown after a successful password change via allauth."""
    messages.success(request, _("Your password has been changed successfully."))
    return redirect("accounts:overview")


# ─── Security / MFA Status ────────────────────────────────────────────────────


@login_required
def security_overview(request):
    """
    Security overview page — MFA status, active sessions, locked state.
    """
    from django_otp import devices_for_user

    from .middleware import user_has_mfa

    totp_devices = list(devices_for_user(request.user, confirmed=True))
    backup_devices = list(devices_for_user(request.user, confirmed=None))

    context = {
        "totp_devices": totp_devices,
        "backup_devices": backup_devices,
        # django-otp devices OR allauth MFA authenticators (TOTP/WebAuthn).
        "mfa_enabled": len(totp_devices) > 0 or user_has_mfa(request.user),
        "meta_title": _("Account Security") + f" — {settings.SITE_NAME}",
    }
    return render(request, "account/security.html", context)


# ─── Logout (POST-only, CSRF-protected) ───────────────────────────────────────


@require_POST
@login_required
def logout_view(request):
    """
    Secure logout — POST only to prevent CSRF-based logouts.
    Logs the action before destroying the session.
    """
    AuditLog.log(
        who=request.user,
        action=AuditLog.Action.LOGOUT,
        description="User logged out.",
        request=request,
    )
    auth_logout(request)
    messages.info(request, _("You have been logged out."))
    return redirect(settings.LOGOUT_REDIRECT_URL)


# ─── Dashboard Redirect ────────────────────────────────────────────────────────


@login_required
def dashboard_redirect(request):
    """
    Smart redirect after login:
    - Staff/superuser/lecturer → Academic Dashboard
    - Others                  → Homepage
    """
    user = request.user
    if user.is_staff or user.is_superuser or user.is_editor_or_above:
        return redirect("core:dashboard")
    return redirect("core:home")


# ─── Admin Panel User Management (staff only) ─────────────────────────────────


@login_required
def user_list(request):
    """List all users. Staff/Admin only."""
    if not request.user.is_admin_or_above:
        messages.error(request, _("You do not have permission to view this page."))
        return redirect("core:home")

    # Paginate: the list template iterates every row, so an unfiltered
    # queryset loads all accounts (plus a second COUNT for the header badge)
    # on each request and grows without bound.
    users_qs = CustomUser.objects.all().order_by("role", "email")
    paginator = Paginator(users_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "users": page_obj,
        "page_obj": page_obj,
        "total_users": paginator.count,
        "meta_title": _("User Management") + f" — {settings.SITE_NAME}",
    }
    return render(request, "admin_panel/users/list.html", context)


@login_required
def user_detail(request, pk):
    """View a single user's details. Staff/Admin only."""
    from django.shortcuts import get_object_or_404

    if not request.user.is_admin_or_above:
        messages.error(request, _("You do not have permission to view this page."))
        return redirect("core:home")

    user = get_object_or_404(CustomUser, pk=pk)
    audit_logs = AuditLog.objects.filter(user=user).order_by("-timestamp")[:20]

    context = {
        "target_user": user,
        "audit_logs": audit_logs,
        "meta_title": f"{user.get_full_name()} — {settings.SITE_NAME}",
    }
    return render(request, "admin_panel/users/detail.html", context)


@login_required
def toggle_user_active(request, pk):
    """Activate or deactivate a user account. Admin only. POST required."""
    from django.shortcuts import get_object_or_404

    if not request.user.is_admin_or_above or request.method != "POST":
        return redirect("accounts:user_list")

    user = get_object_or_404(CustomUser, pk=pk)
    if user == request.user:
        messages.error(request, _("You cannot deactivate your own account."))
        return redirect("accounts:user_detail", pk=pk)

    # Role hierarchy: only a superadmin may touch superadmins; otherwise
    # nobody may change an account at or above their own role.
    _role_rank = {
        CustomUser.Role.STUDENT: 0,
        CustomUser.Role.RESEARCHER: 1,
        CustomUser.Role.EDITOR: 2,
        CustomUser.Role.LECTURER: 3,
        CustomUser.Role.ADMIN: 4,
        CustomUser.Role.SUPERADMIN: 5,
    }
    is_super = request.user.role == CustomUser.Role.SUPERADMIN
    if not is_super and _role_rank.get(user.role, 0) >= _role_rank.get(request.user.role, 0):
        messages.error(request, _("You cannot change an account at or above your role."))
        return redirect("accounts:user_list")

    # Last-superadmin guard: never deactivate the final active superadmin.
    if user.role == CustomUser.Role.SUPERADMIN and user.is_active:
        remaining = (
            CustomUser.objects.filter(role=CustomUser.Role.SUPERADMIN, is_active=True).exclude(pk=user.pk).count()
        )
        if remaining == 0:
            messages.error(request, _("Cannot deactivate the last active superadmin."))
            return redirect("accounts:user_detail", pk=pk)

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    action = AuditLog.Action.USER_ACTIVATED if user.is_active else AuditLog.Action.USER_DEACTIVATED
    AuditLog.log(
        who=request.user,
        action=action,
        obj=user,
        description=f"User {'activated' if user.is_active else 'deactivated'}: {user.email}",
        request=request,
    )
    msg = _("User activated.") if user.is_active else _("User deactivated.")
    messages.success(request, msg)
    return redirect("accounts:user_detail", pk=pk)
