"""
Permission mixins and decorators for RBAC.
"""

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.accounts.models import CustomUser


class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin that requires one or more roles."""

    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.required_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles = [CustomUser.Role.SUPERADMIN, CustomUser.Role.ADMIN]


class LecturerOrAboveMixin(RoleRequiredMixin):
    required_roles = [
        CustomUser.Role.SUPERADMIN,
        CustomUser.Role.ADMIN,
        CustomUser.Role.LECTURER,
    ]


class EditorOrAboveMixin(RoleRequiredMixin):
    required_roles = [
        CustomUser.Role.SUPERADMIN,
        CustomUser.Role.ADMIN,
        CustomUser.Role.LECTURER,
        CustomUser.Role.EDITOR,
    ]


def role_required(*roles):
    """Function decorator for role-based access."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("account_login")
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
