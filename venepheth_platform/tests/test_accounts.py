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

    def test_promotion_to_admin_enables_require_mfa(self, user):
        from django.contrib.auth import get_user_model

        user.role = get_user_model().Role.ADMIN
        user.save()
        user.refresh_from_db()
        assert user.require_mfa is True
