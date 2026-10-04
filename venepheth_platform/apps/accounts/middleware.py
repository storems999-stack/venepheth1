"""
Enforcement middleware for step-up security controls.

`require_mfa` and `must_change_password` are stored on the user, but flags
alone do nothing — this middleware makes them fail-closed by redirecting
non-compliant sessions before any view runs.
"""

import logging
from contextlib import ExitStack
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.accounts")

# URL prefixes that must stay reachable while under enforcement
# (login/logout, password recovery, password change, and MFA setup).
_ALWAYS_ALLOWED_PREFIXES = (
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/password/change/",
    "/accounts/password/set/",
    "/accounts/password/reset/",
    "/accounts/confirm-email/",
    "/accounts/login/code/",
    "/accounts/2fa/",
    "/my/logout/",
    "/my/password/",
    "/i18n/",
    "/health",
    "/ready",
    "/live",
    "/metrics",
)

_API_PREFIX = "/api/"


class UserPreferenceMiddleware:
    """Apply authenticated users' saved language and timezone preferences."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)

        language = None
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            preferred_language = getattr(user, "language", "")
            if preferred_language in dict(settings.LANGUAGES):
                language = preferred_language
                request.LANGUAGE_CODE = preferred_language
            elif preferred_language:
                logger.warning("Ignoring unsupported language preference for user pk=%s", user.pk)

        preferred_timezone = getattr(user, "timezone", "")
        try:
            user_timezone = ZoneInfo(preferred_timezone) if preferred_timezone else None
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            logger.warning("Ignoring unsupported timezone preference for user pk=%s", user.pk)
            user_timezone = None

        with ExitStack() as stack:
            if language:
                stack.enter_context(translation.override(language))
            if user_timezone:
                stack.enter_context(timezone.override(user_timezone))
            response = self.get_response(request)

        if language:
            response.headers.setdefault("Content-Language", language)
        if language or user_timezone:
            patch_vary_headers(response, ("Cookie",))
        return response


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
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in _ALWAYS_ALLOWED_PREFIXES):
            return None
        if any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in (settings.STATIC_URL, settings.MEDIA_URL)
        ):
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
