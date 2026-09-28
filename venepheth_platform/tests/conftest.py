"""
Pytest configuration and global fixtures.
"""

import pytest
from django.test import Client
from rest_framework.test import APIClient

from tests.factories import (
    AdminUserFactory,
    ArticleFactory,
    CourseFactory,
    LecturerUserFactory,
    PublicationFactory,
    ResearchProjectFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    """Unauthenticated DRF API client."""
    return APIClient()


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


@pytest.fixture
def auth_api_client(user):
    """DRF API client authenticated with a standard user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def sample_course(db):
    return CourseFactory.create()


@pytest.fixture
def sample_article(db):
    return ArticleFactory.create()


@pytest.fixture
def sample_publication(db):
    return PublicationFactory.create()


@pytest.fixture
def sample_project(db):
    return ResearchProjectFactory.create()
