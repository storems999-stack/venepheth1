"""
Enforcement middleware for step-up security controls.

`require_mfa` and `must_change_password` are stored on the user, but flags
alone do nothing — this middleware makes them fail-closed by redirecting
non-compliant sessions before any view runs.
"""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.accounts")

# URL path fragments that must stay reachable while under enforcement
# (setup flows, logout, password flows) — otherwise users get redirect loops.
_ALWAYS_ALLOWED_SUBSTRINGS = (
    "logout",
    "password",
    "2fa",
    "mfa",
    "reauthenticate",
    "confirm-email",
)

# Path prefixes that bypass enforcement entirely (infra / non-HTML endpoints).
_ALWAYS_ALLOWED_PREFIXES = (
    "/i18n/",
    "/health/",
    "/ready/",
    "/live/",
    "/metrics/",
)

_API_PREFIX = "/api/"


def user_has_mfa(user) -> bool:
    """True when the user has a second factor (TOTP/WebAuthn, not just recovery codes)."""
    try:
        from allauth.mfa.models import Authenticator

        return Authenticator.objects.filter(user=user).exclude(type=Authenticator.Type.RECOVERY_CODES).exists()
    except Exception:
        # Fail-closed: a broken MFA check must not grant access.
        logger.exception("MFA status check failed for user pk=%s", getattr(user, "pk", "?"))
        return False


class SecurityEnforcementMiddleware(MiddlewareMixin):
    """
    Redirect sessions that have not satisfied mandatory security controls.

    - `must_change_password` → allauth password change page.
    - `require_mfa` without a configured authenticator → allauth MFA setup page.
    - API requests under enforcement get 403 JSON instead of a redirect.
    """

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        path = request.path
        if path.startswith(_ALWAYS_ALLOWED_PREFIXES):
            return None
        if path.startswith((settings.STATIC_URL, settings.MEDIA_URL)):
            return None
        if any(fragment in path for fragment in _ALWAYS_ALLOWED_SUBSTRINGS):
            return None

        must_change = getattr(user, "must_change_password", False)
        require_mfa = getattr(user, "require_mfa", False)
        if not must_change and not require_mfa:
            return None

        if path.startswith(_API_PREFIX):
            return JsonResponse({"detail": "Security action required."}, status=403)

        if must_change:
            return redirect(reverse("account_change_password"))
        if require_mfa and not user_has_mfa(user):
            return redirect(reverse("mfa_index"))
        return None
