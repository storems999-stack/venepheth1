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
