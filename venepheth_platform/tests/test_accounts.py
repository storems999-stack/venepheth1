"""
Tests for Phase 2: Accounts, Profile, Security, and 2FA views.
"""

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog


@pytest.mark.django_db
class TestAccountViews:
    def test_overview_unauthenticated_redirects_login(self, client):
        url = reverse("accounts:overview")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_overview_authenticated(self, auth_client, user):
        url = reverse("accounts:overview")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert user.email in response.content.decode()

    def test_profile_edit_get(self, auth_client, user):
        url = reverse("accounts:profile_edit")
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_profile_edit_post(self, auth_client, user):
        url = reverse("accounts:profile_edit")
        response = auth_client.post(
            url,
            {
                "first_name": "UpdatedName",
                "last_name": "UpdatedLast",
                "language": "lo",
                "timezone": "Asia/Vientiane",
            },
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.first_name == "UpdatedName"
        assert user.language == "lo"
        # Check audit log entry
        assert AuditLog.objects.filter(user=user, action=AuditLog.Action.UPDATE).exists()

    def test_profile_edit_rejects_unsupported_preferences(self, auth_client, user):
        response = auth_client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": "UpdatedName",
                "last_name": "UpdatedLast",
                "language": "unsupported",
                "timezone": "Invalid/Timezone",
            },
        )

        assert response.status_code == 200
        assert "language" in response.context["form"].errors
        assert "timezone" in response.context["form"].errors
        assert b"Select a valid choice." in response.content

        user.refresh_from_db()
        assert user.language == "en"
        assert user.timezone == "Asia/Vientiane"

    def test_saved_user_preferences_are_applied_to_requests(self, user):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from django.utils import timezone, translation

        from apps.accounts.middleware import UserPreferenceMiddleware

        user.language = "lo"
        user.timezone = "Asia/Tokyo"
        user.save(update_fields=["language", "timezone"])

        def read_preferences(request):
            return HttpResponse(
                f"{translation.get_language()}|{timezone.get_current_timezone_name()}|{request.LANGUAGE_CODE}"
            )

        request = RequestFactory().get("/")
        request.user = user
        request.COOKIES = {}

        response = UserPreferenceMiddleware(read_preferences)(request)

        assert response.content.decode() == "lo|Asia/Tokyo|lo"
        assert translation.get_language() == "en"
        assert timezone.get_current_timezone_name() == "Asia/Vientiane"

    def test_saved_language_is_used_on_authenticated_page(self, auth_client, user):
        user.language = "lo"
        user.save(update_fields=["language"])

        response = auth_client.get(reverse("core:home"))

        assert response.status_code == 200
        assert response["Content-Language"] == "lo"
        assert "Cookie" in response.get("Vary", "")
        assert "ໜ້າຫຼັກ" in response.content.decode()

    def test_cached_course_list_respects_each_users_language(self, user):
        from django.core.cache import cache
        from django.test import Client

        cache.clear()
        lao_user = type(user).objects.create_user(
            email="lao-preference@test.com",
            password="TestPassword123!",
            language="lo",
        )
        user.language = "en"
        user.save(update_fields=["language"])

        english_client = Client()
        english_client.force_login(user)
        lao_client = Client()
        lao_client.force_login(lao_user)

        english_response = english_client.get(reverse("courses:list"))
        lao_response = lao_client.get(reverse("courses:list"))

        assert english_response["Content-Language"] == "en"
        assert lao_response["Content-Language"] == "lo"
        assert ">Courses<" in english_response.content.decode()
        assert "ວິຊາຮຽນ" in lao_response.content.decode()

    def test_language_cookie_overrides_saved_language_preference(self, user):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from django.utils import timezone, translation

        from apps.accounts.middleware import UserPreferenceMiddleware

        user.language = "en"
        user.timezone = "Asia/Tokyo"
        user.save(update_fields=["language", "timezone"])
        request = RequestFactory().get("/")
        request.user = user
        request.COOKIES = {"django_language": "lo"}
        request.LANGUAGE_CODE = "lo"

        with translation.override("lo"):
            response = UserPreferenceMiddleware(
                lambda request: HttpResponse(f"{translation.get_language()}|{timezone.get_current_timezone_name()}")
            )(request)

        assert response.content.decode() == "lo|Asia/Tokyo"
        assert request.LANGUAGE_CODE == "lo"

    def test_security_overview(self, auth_client):
        url = reverse("accounts:security")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "Two-Factor Authentication" in response.content.decode()

    def test_logout_get_method_not_allowed(self, auth_client):
        url = reverse("accounts:logout")
        response = auth_client.get(url)
        assert response.status_code == 405  # POST required

    def test_logout_post_success(self, auth_client, user):
        url = reverse("accounts:logout")
        response = auth_client.post(url)
        assert response.status_code == 302
        # Check logout audit log
        assert AuditLog.objects.filter(user=user, action=AuditLog.Action.LOGOUT).exists()

    def test_dashboard_redirect_regular_user(self, auth_client):
        url = reverse("accounts:dashboard_redirect")
        response = auth_client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("core:home")

    def test_dashboard_redirect_lecturer_user(self, lecturer_user):
        from django.test import Client

        c = Client()
        c.force_login(lecturer_user)
        url = reverse("accounts:dashboard_redirect")
        response = c.get(url)
        assert response.status_code == 302
        assert response.url == reverse("core:dashboard")

    def test_dashboard_redirect_does_not_send_non_staff_editor_to_denied_dashboard(self, db):
        from django.contrib.auth import get_user_model
        from django.test import Client

        user_model = get_user_model()
        editor = user_model.objects.create_user(
            email="editor-without-staff@example.com",
            password="TestPass123456!",
            role=user_model.Role.EDITOR,
            is_staff=False,
        )
        c = Client()
        c.force_login(editor)

        response = c.get(reverse("accounts:dashboard_redirect"))

        assert response.status_code == 302
        assert response.url == reverse("core:home")

    def test_admin_user_list_forbidden_for_regular_user(self, auth_client):
        url = reverse("accounts:user_list")
        response = auth_client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("core:home")

    def test_admin_user_list_allowed_for_admin(self, admin_client):
        url = reverse("accounts:user_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_admin_toggle_user_active(self, admin_client, user):
        url = reverse("accounts:toggle_user_active", kwargs={"pk": user.pk})
        assert user.is_active is True
        response = admin_client.post(url)
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.is_active is False


@pytest.mark.django_db
class TestSignupClosed:
    """Public registration is disabled — admins create accounts."""

    def test_signup_page_redirects_away(self, client):
        response = client.get(reverse("account_signup"))
        assert response.status_code == 302
        assert response.url == "/accounts/login/"

    def test_signup_post_creates_no_user(self, client):
        from django.contrib.auth import get_user_model

        before = get_user_model().objects.count()
        client.post(
            reverse("account_signup"),
            {"email": "new@test.com", "password1": "TestPass123456!", "password2": "TestPass123456!"},
        )
        assert get_user_model().objects.count() == before


@pytest.mark.django_db
class TestSecurityEnforcement:
    """require_mfa / must_change_password must be fail-closed (middleware)."""

    def _login(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_require_mfa_without_authenticator_redirects(self, user):
        user.require_mfa = True
        user.save(update_fields=["require_mfa"])
        response = self._login(user).get(reverse("accounts:overview"))
        assert response.status_code == 302
        assert response.url == reverse("mfa_index")

    def test_require_mfa_with_authenticator_passes(self, user):
        from allauth.mfa.models import Authenticator

        user.require_mfa = True
        user.save(update_fields=["require_mfa"])
        Authenticator.objects.create(user=user, type=Authenticator.Type.TOTP, data={"secret": "TEST"})
        assert self._login(user).get(reverse("accounts:overview")).status_code == 200

    def test_must_change_password_redirects(self, user):
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        response = self._login(user).get(reverse("accounts:overview"))
        assert response.status_code == 302
        assert response.url == reverse("account_change_password")

    def test_password_change_page_reachable_while_enforced(self, user):
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        assert self._login(user).get(reverse("account_change_password")).status_code == 200

    def test_email_management_does_not_bypass_required_password_change(self, user):
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        response = self._login(user).get("/accounts/email/")
        assert response.status_code == 302
        assert response.url == reverse("account_change_password")

    def test_email_management_does_not_bypass_required_mfa(self, user):
        user.require_mfa = True
        user.save(update_fields=["require_mfa"])
        response = self._login(user).get("/accounts/email/")
        assert response.status_code == 302
        assert response.url == reverse("mfa_index")

    def test_enforcement_api_returns_403(self, user):
        # Session-authenticated API request still passes through middleware.
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        response = self._login(user).get(reverse("api:article-list"), HTTP_ACCEPT="application/json")
        assert response.status_code == 403

    def test_admin_cannot_toggle_superadmin(self, admin_client):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        sup = User.objects.create_user(email="sup@test.com", password="TestPass123456!", role=User.Role.SUPERADMIN)
        url = reverse("accounts:toggle_user_active", kwargs={"pk": sup.pk})
        assert admin_client.post(url).status_code == 302
        sup.refresh_from_db()
        assert sup.is_active is True

    def test_admin_cannot_toggle_django_superuser_with_mismatched_role(self, admin_client):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        sup = User.objects.create_user(
            email="role-mismatch-superuser@test.com",
            password="TestPass123456!",
            role=User.Role.STUDENT,
            is_superuser=True,
        )
        url = reverse("accounts:toggle_user_active", kwargs={"pk": sup.pk})
        assert admin_client.post(url).status_code == 302
        sup.refresh_from_db()
        assert sup.is_active is True

    def test_superadmin_can_deactivate_mismatched_superuser_if_another_remains(self, db):
        from allauth.mfa.models import Authenticator
        from django.contrib.auth import get_user_model
        from django.test import Client

        User = get_user_model()
        target = User.objects.create_user(
            email="mismatched-superuser@test.com",
            password="TestPass123456!",
            role=User.Role.STUDENT,
            is_superuser=True,
        )
        superadmin = User.objects.create_user(
            email="role-aligned-superadmin@test.com",
            password="TestPass123456!",
            role=User.Role.SUPERADMIN,
        )
        Authenticator.objects.create(user=superadmin, type=Authenticator.Type.TOTP, data={"secret": "TEST"})
        client = Client()
        client.force_login(superadmin)
        url = reverse("accounts:toggle_user_active", kwargs={"pk": target.pk})
        assert client.post(url).status_code == 302
        target.refresh_from_db()
        assert target.is_active is False
        superadmin.refresh_from_db()
        assert superadmin.is_active is True

    def test_superadmin_can_toggle_admin(self, db):
        from allauth.mfa.models import Authenticator
        from django.contrib.auth import get_user_model
        from django.test import Client

        User = get_user_model()
        sup = User.objects.create_user(email="sup2@test.com", password="TestPass123456!", role=User.Role.SUPERADMIN)
        Authenticator.objects.create(user=sup, type=Authenticator.Type.TOTP, data={"secret": "TEST"})
        target = User.objects.create_user(
            email="adm@test.com", password="TestPass123456!", role=User.Role.ADMIN, is_staff=True
        )
        c = Client()
        c.force_login(sup)
        url = reverse("accounts:toggle_user_active", kwargs={"pk": target.pk})
        assert c.post(url).status_code == 302
        target.refresh_from_db()
        assert target.is_active is False

    def test_enforcement_not_bypassed_by_substring_path(self, user):
        """A URL merely containing 'password' must not skip enforcement."""
        user.require_mfa = True
        user.save(update_fields=["require_mfa"])
        response = self._login(user).get("/blog/password-tips/")
        assert response.status_code == 302
        assert response.url == reverse("mfa_index")

    def test_password_reset_clears_must_change(self, user):
        from allauth.account.signals import password_reset

        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        password_reset.send(sender=None, request=None, user=user)
        user.refresh_from_db()
        assert user.must_change_password is False

    def test_promotion_to_admin_enables_require_mfa(self, user):
        from django.contrib.auth import get_user_model

        user.role = get_user_model().Role.ADMIN
        user.save()
        user.refresh_from_db()
        assert user.require_mfa is True
