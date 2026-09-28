"""Security hardening tests (Vision §14, §15, §17, §21)."""

import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.security.models import SecurityEvent


class MFATests(TestCase):
    """Verify MFA/2FA is wired and accessible (Vision §15)."""

    def setUp(self):
        self.user = self._create_staff_user()

    def _create_staff_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_user(
            email="lecturer@test.com",
            password="SecurePass123!",
            is_staff=True,
            first_name="Test",
            last_name="Lecturer",
        )

    def test_allauth_mfa_in_installed_apps(self):
        """allauth.mfa must be in INSTALLED_APPS."""
        from django.apps import apps

        app_labels = [app.label for app in apps.get_app_configs()]
        self.assertIn("mfa", app_labels)
        self.assertIn("otp_totp", app_labels)
        self.assertIn("otp_static", app_labels)

    def test_mfa_url_resolves(self):
        """MFA URL (/accounts/2fa/) must be accessible."""
        response = self.client.get("/accounts/2fa/")
        self.assertIn(response.status_code, [200, 302])

    def test_user_has_require_mfa_field(self):
        """CustomUser must have require_mfa field."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(email="test2@test.com", password="SecurePass123!", is_staff=False)
        self.assertTrue(hasattr(user, "require_mfa"))

    def test_admin_auto_requires_mfa(self):
        """Admin/SUPERADMIN users must auto-enable require_mfa (signals)."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_user(
            email="admin@test.com",
            password="SecurePass123!",
            is_staff=True,
            role=User.Role.ADMIN,
        )
        admin.refresh_from_db()
        self.assertTrue(admin.require_mfa)

    def test_audit_log_records_login(self):
        """Login must create an audit log entry."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(email="audit@test.com", password="SecurePass123!", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        audit_count = AuditLog.objects.filter(user_email="audit@test.com", action=AuditLog.Action.LOGIN).count()
        self.assertGreater(audit_count, 0)

    def test_security_event_records_login_failure(self):
        """Failed login triggers SecurityEvent via signal."""
        from django.contrib.auth import get_user_model
        from django.contrib.auth.signals import user_login_failed

        User = get_user_model()
        user = User.objects.create_user(email="fail@test.com", password="SecurePass123!", is_staff=False)
        request = type(
            "Req",
            (),
            {
                "META": {
                    "REMOTE_ADDR": "127.0.0.1",
                    "HTTP_USER_AGENT": "test-client",
                },
                "path": "/accounts/login/",
            },
        )()
        user_login_failed.send(
            sender="test",
            credentials={"email": "fail@test.com"},
            request=request,
            user=user,
        )
        event_count = SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.LOGIN_FAILURE).count()
        self.assertGreater(event_count, 0)


class FileUploadSecurityTests(TestCase):
    """Verify file upload validation on all file-bearing models (Vision §21)."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def _make_pdf(self, filename="test.pdf"):
        return SimpleUploadedFile(
            filename,
            b"%PDF-1.4 fake pdf content",
            content_type="application/pdf",
        )

    def _make_exe(self, filename="malware.exe"):
        return SimpleUploadedFile(
            filename,
            b"MZ fake executable",
            content_type="application/octet-stream",
        )

    # ── Course.thumbnail ─────────────────────────────────────────

    def test_course_thumbnail_accepts_pdf(self):
        from apps.courses.models import Course, CourseCategory

        cat = CourseCategory.objects.create(name="Test", slug="test")
        course = Course.objects.create(
            name="Test Course",
            slug="test-course",
            code="T101",
            category=cat,
            description="desc",
        )
        course.thumbnail = self._make_pdf("slide.pdf")
        course.save()
        course.refresh_from_db()
        self.assertIsNotNone(course.thumbnail)

    def test_course_thumbnail_rejects_exe(self):
        from apps.courses.models import Course, CourseCategory

        cat = CourseCategory.objects.create(name="Test", slug="test")
        course = Course.objects.create(
            name="Test Course",
            slug="test-course",
            code="T101",
            category=cat,
            description="desc",
        )
        course.thumbnail = self._make_exe("malware.exe")
        with self.assertRaises(ValidationError):
            course.full_clean()

    # ── ResearchProject.pdf_file ─────────────────────────────────

    def test_publication_pdf_accepts_pdf(self):
        from apps.research.models import Publication

        pub = Publication.objects.create(
            title="Test Paper",
            slug="test-paper",
            publication_type="journal",
            abstract="desc",
            year=2025,
        )
        pub.pdf_file = self._make_pdf("paper.pdf")
        pub.save()
        pub.refresh_from_db()
        self.assertIsNotNone(pub.pdf_file)

    def test_publication_pdf_rejects_exe(self):
        from apps.research.models import Publication

        pub = Publication.objects.create(
            title="Test Paper",
            slug="test-paper",
            publication_type="journal",
            abstract="desc",
            year=2025,
        )
        pub.pdf_file = self._make_exe("malware.exe")
        with self.assertRaises(ValidationError):
            pub.full_clean()

    # ── Article.thumbnail ────────────────────────────────────────

    def test_article_thumbnail_accepts_image(self):
        from apps.blog.models import Article, ArticleTag

        tag = ArticleTag.objects.create(name="Test", slug="test")
        article = Article.objects.create(
            title="Test Article",
            slug="test-article",
            content_raw="<p>content</p>",
            category="article",
            status="published",
        )
        article.tags.add(tag)
        article.thumbnail = SimpleUploadedFile("thumb.png", b"fake png", content_type="image/png")
        article.save()
        article.refresh_from_db()
        self.assertIsNotNone(article.thumbnail)

    def test_article_thumbnail_rejects_exe(self):
        from apps.blog.models import Article

        article = Article.objects.create(
            title="Test Article",
            slug="test-article",
            content_raw="<p>content</p>",
            category="article",
            status="published",
        )
        article.thumbnail = self._make_exe("malware.exe")
        with self.assertRaises(ValidationError):
            article.full_clean()

    # ── Profile.photo ───────────────────────────────────────────

    def test_profile_photo_accepts_image(self):
        from apps.profiles.models import Profile

        profile = Profile.objects.create(full_name="Test User", email="test@example.com")
        profile.photo = SimpleUploadedFile("photo.jpg", b"fake jpg", content_type="image/jpeg")
        profile.save()
        profile.refresh_from_db()
        self.assertIsNotNone(profile.photo)

    def test_profile_photo_rejects_exe(self):
        from apps.profiles.models import Profile

        profile = Profile.objects.create(full_name="Test User", email="test@example.com")
        profile.photo = self._make_exe("malware.exe")
        with self.assertRaises(ValidationError):
            profile.full_clean()

    # ── Resource.file (already had validators — verify they work) ─

    def test_resource_file_accepts_pdf(self):
        from apps.resources.models import Resource, ResourceCategory

        cat = ResourceCategory.objects.create(name="Docs", slug="docs")
        resource = Resource.objects.create(
            title="Test Resource",
            slug="test-resource",
            category=cat,
        )
        resource.file = self._make_pdf("notes.pdf")
        resource.save()
        resource.refresh_from_db()
        self.assertIsNotNone(resource.file)

    def test_resource_file_rejects_exe(self):
        from apps.resources.models import Resource, ResourceCategory

        cat = ResourceCategory.objects.create(name="Docs", slug="docs")
        resource = Resource.objects.create(
            title="Test Resource",
            slug="test-resource",
            category=cat,
        )
        resource.file = self._make_exe("malware.exe")
        with self.assertRaises(ValidationError):
            resource.full_clean()

    def test_resource_file_rejects_oversize(self):
        from django.conf import settings

        from apps.resources.models import Resource, ResourceCategory

        cat = ResourceCategory.objects.create(name="Docs", slug="docs")
        resource = Resource.objects.create(
            title="Test Resource",
            slug="test-resource",
            category=cat,
        )
        oversized = SimpleUploadedFile(
            "big.pdf",
            b"x" * (settings.MAX_UPLOAD_SIZE + 1),
            content_type="application/pdf",
        )
        resource.file = oversized
        with self.assertRaises(ValidationError):
            resource.full_clean()
