"""
Pytest configuration and global fixtures.
"""

import pytest
from django.test import Client

from tests.factories import AdminUserFactory, LecturerUserFactory, UserFactory


@pytest.fixture
def user(db):
    """Standard student user."""
    return UserFactory.create()


@pytest.fixture
def admin_user(db):
    """Staff/superuser admin with MFA configured (passes security enforcement)."""
    from allauth.mfa.models import Authenticator

    admin = AdminUserFactory.create()
    Authenticator.objects.create(user=admin, type=Authenticator.Type.TOTP, data={"secret": "TESTSECRET"})
    return admin


@pytest.fixture
def lecturer_user(db):
    """Lecturer user with MFA configured (passes security enforcement)."""
    from allauth.mfa.models import Authenticator

    lecturer = LecturerUserFactory.create()
    Authenticator.objects.create(user=lecturer, type=Authenticator.Type.TOTP, data={"secret": "TESTSECRET"})
    return lecturer


@pytest.fixture
def auth_client(user):
    """Client authenticated with a standard user."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Client authenticated with an admin user."""
    client = Client()
    client.force_login(admin_user)
    return client
