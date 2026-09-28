"""Tests for permission-checked file downloads (no direct /media/ links)."""

import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.courses.models import Course, CourseResource
from apps.research.models import Publication
from apps.resources.models import Resource

PDF = SimpleUploadedFile("test.pdf", b"%PDF-1.4 fake-content", content_type="application/pdf")


def _pdf(name="test.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake-content", content_type="application/pdf")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ResourceDownloadTests(TestCase):
    def _make(self, visibility, **kwargs):
        return Resource.objects.create(
            title=f"Res {visibility}",
            slug=f"res-{visibility}-{Resource.objects.count()}",
            visibility=visibility,
            file=_pdf(),
            **kwargs,
        )

    def test_public_download_200_and_counts(self):
        res = self._make(Resource.Visibility.PUBLIC)
        resp = self.client.get(reverse("resources:download", kwargs={"slug": res.slug}))
        self.assertEqual(resp.status_code, 200)
        res.refresh_from_db()
        self.assertEqual(res.download_count, 1)

    def test_students_anonymous_redirects_login(self):
        res = self._make(Resource.Visibility.STUDENTS)
        resp = self.client.get(reverse("resources:download", kwargs={"slug": res.slug}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_students_authenticated_ok(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(email="s@test.com", password="SecurePass123!")
        self.client.force_login(user)
        res = self._make(Resource.Visibility.STUDENTS)
        self.assertEqual(
            self.client.get(reverse("resources:download", kwargs={"slug": res.slug})).status_code,
            200,
        )

    def test_private_404_even_authenticated(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(email="s2@test.com", password="SecurePass123!")
        self.client.force_login(user)
        res = self._make(Resource.Visibility.PRIVATE)
        self.assertEqual(
            self.client.get(reverse("resources:download", kwargs={"slug": res.slug})).status_code,
            404,
        )

    @override_settings(SENDFILE_ENABLED=True)
    def test_sendfile_uses_accel_redirect(self):
        res = self._make(Resource.Visibility.PUBLIC)
        resp = self.client.get(reverse("resources:download", kwargs={"slug": res.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Accel-Redirect"], f"/protected-media/{res.file.name}")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PublicationDownloadTests(TestCase):
    def _make(self, status, **kwargs):
        n = Publication.objects.count()
        return Publication.objects.create(
            title=f"Pub {n}",
            slug=f"pub-{n}",
            status=status,
            publication_type=Publication.PublicationType.JOURNAL,
            authors="A U Thor",
            year=2026,
            pdf_file=_pdf(f"pub-{n}.pdf"),
            **kwargs,
        )

    def test_published_pdf_200(self):
        pub = self._make("published")
        self.assertEqual(
            self.client.get(reverse("publications:download", kwargs={"slug": pub.slug})).status_code,
            200,
        )

    def test_draft_pdf_404(self):
        pub = self._make("draft")
        self.assertEqual(
            self.client.get(reverse("publications:download", kwargs={"slug": pub.slug})).status_code,
            404,
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseResourceDownloadTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            name="C",
            slug="c",
            code="C101",
            description="d",
            status="published",
            visibility="public",
        )

    def _make(self, visibility):
        return CourseResource.objects.create(
            course=self.course,
            title=f"CR {visibility}",
            visibility=visibility,
            file=_pdf(f"cr-{visibility}.pdf"),
        )

    def test_public_200(self):
        res = self._make("public")
        resp = self.client.get(reverse("courses:resource_download", kwargs={"pk": res.pk}))
        self.assertEqual(resp.status_code, 200)
        res.refresh_from_db()
        self.assertEqual(res.download_count, 1)

    def test_private_404(self):
        res = self._make("private")
        self.assertEqual(
            self.client.get(reverse("courses:resource_download", kwargs={"pk": res.pk})).status_code,
            404,
        )

    def test_hidden_course_404(self):
        self.course.visibility = "private"
        self.course.save(update_fields=["visibility"])
        res = self._make("public")
        self.assertEqual(
            self.client.get(reverse("courses:resource_download", kwargs={"pk": res.pk})).status_code,
            404,
        )
