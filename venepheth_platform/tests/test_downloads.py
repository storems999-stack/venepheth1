"""Tests for permission-checked file downloads (no direct /media/ links)."""

import hashlib
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.courses.models import Course, CourseModule, CourseResource
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

    def test_students_only_resource_rejects_authenticated_non_student(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="editor@test.com",
            password="TestPass123456!",
            role=get_user_model().Role.EDITOR,
        )
        self.client.force_login(user)
        res = self._make(Resource.Visibility.STUDENTS)

        response = self.client.get(reverse("resources:download", kwargs={"slug": res.slug}))

        self.assertEqual(response.status_code, 404)

    def test_students_only_resource_detail_rejects_authenticated_non_student(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="detail-editor@test.com",
            password="TestPass123456!",
            role=get_user_model().Role.EDITOR,
        )
        self.client.force_login(user)
        res = self._make(Resource.Visibility.STUDENTS)

        response = self.client.get(reverse("resources:detail", kwargs={"slug": res.slug}))

        self.assertEqual(response.status_code, 404)

    def test_private_404_even_authenticated(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(email="s2@test.com", password="SecurePass123!")
        self.client.force_login(user)
        res = self._make(Resource.Visibility.PRIVATE)
        self.assertEqual(
            self.client.get(reverse("resources:download", kwargs={"slug": res.slug})).status_code,
            404,
        )

    def test_protected_files_are_not_directly_accessible_through_media_routes(self):
        protected_paths = ("resources/files", "publications/pdfs", "courses/resources", "assistant/knowledge")
        for index, protected_path in enumerate(protected_paths):
            with self.subTest(path=protected_path):
                protected_root = Path(settings.MEDIA_ROOT) / protected_path
                protected_root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=protected_root) as media_dir:
                    private_file = Path(media_dir) / f"private-{index}.pdf"
                    private_file.write_bytes(b"private content")
                    media_path = private_file.relative_to(settings.MEDIA_ROOT).as_posix()

                    response = self.client.get(f"{settings.MEDIA_URL}{media_path}")

                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.resolver_match.func.__name__, "protected_media_not_found")

    @override_settings(SENDFILE_ENABLED=True)
    def test_sendfile_uses_accel_redirect(self):
        res = self._make(Resource.Visibility.PUBLIC)
        resp = self.client.get(reverse("resources:download", kwargs={"slug": res.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Accel-Redirect"], f"/protected-media/{res.file.name}")

    def test_replacing_resource_file_refreshes_file_metadata(self):
        res = self._make(Resource.Visibility.PUBLIC)
        replacement_content = b"%PDF-1.7 replacement document"

        res.file = SimpleUploadedFile("replacement.pdf", replacement_content, content_type="application/pdf")
        res.save(update_fields=["file"])

        res.refresh_from_db()
        self.assertEqual(res.file_size, len(replacement_content))
        self.assertEqual(res.file_hash, hashlib.sha256(replacement_content).hexdigest())

    def test_replacing_resource_file_with_generator_update_fields_persists_file(self):
        res = self._make(Resource.Visibility.PUBLIC)
        old_name = res.file.name
        res.file = SimpleUploadedFile("replacement.pdf", b"%PDF-1.7 replacement", content_type="application/pdf")
        res.save(update_fields=(field for field in ["file"]))

        res.refresh_from_db()
        self.assertNotEqual(res.file.name, old_name)

    def test_removing_resource_file_clears_file_metadata(self):
        res = self._make(Resource.Visibility.PUBLIC)

        res.file.delete(save=False)
        res.save(update_fields=["file"])

        res.refresh_from_db()
        self.assertIsNone(res.file_size)
        self.assertEqual(res.file_hash, "")


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

    def test_publication_api_returns_protected_download_url(self):
        pub = self._make("published")
        response = self.client.get(reverse("api:publication-detail", kwargs={"slug": pub.slug}))
        self.assertEqual(response.status_code, 200)
        path = reverse("publications:download", kwargs={"slug": pub.slug})
        self.assertTrue(response.json()["pdf_file"].endswith(path))
        self.assertNotIn("/media/", response.json()["pdf_file"])


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

    def test_students_only_resource_rejects_authenticated_non_student(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="course-editor@test.com",
            password="TestPass123456!",
            role=get_user_model().Role.EDITOR,
        )
        self.client.force_login(user)
        res = self._make(CourseResource.Visibility.STUDENTS)

        response = self.client.get(reverse("courses:resource_download", kwargs={"pk": res.pk}))

        self.assertEqual(response.status_code, 404)

    def test_students_only_resource_is_visible_to_student_on_course_detail(self):
        from django.contrib.auth import get_user_model

        resource = self._make(CourseResource.Visibility.STUDENTS)
        detail_url = reverse("courses:detail", kwargs={"slug": self.course.slug})
        anonymous_response = self.client.get(detail_url)
        self.assertNotContains(anonymous_response, resource.title)

        student = get_user_model().objects.create_user(
            email="course-student@test.com",
            password="TestPass123456!",
            role=get_user_model().Role.STUDENT,
        )
        self.client.force_login(student)
        student_response = self.client.get(detail_url)

        self.assertContains(student_response, resource.title)
        self.assertContains(
            student_response,
            reverse("courses:resource_download", kwargs={"pk": resource.pk}),
        )

    def test_students_only_course_resource_allows_student_download(self):
        from django.contrib.auth import get_user_model

        student = get_user_model().objects.create_user(
            email="download-student@test.com",
            password="TestPass123456!",
            role=get_user_model().Role.STUDENT,
        )
        self.client.force_login(student)
        resource = self._make(CourseResource.Visibility.STUDENTS)

        response = self.client.get(reverse("courses:resource_download", kwargs={"pk": resource.pk}))

        self.assertEqual(response.status_code, 200)

    def test_resource_from_another_course_cannot_be_downloaded_through_module(self):
        module = CourseModule.objects.create(course=self.course, title="Shared module")
        other_course = Course.objects.create(
            name="Other",
            slug="other",
            code="O101",
            description="Other course",
            status="published",
            visibility=Course.Visibility.PUBLIC,
        )
        resource = CourseResource.objects.create(
            course=other_course,
            module=module,
            title="Misassigned material",
            visibility=CourseResource.Visibility.PUBLIC,
            file=_pdf("misassigned.pdf"),
        )

        response = self.client.get(reverse("courses:resource_download", kwargs={"pk": resource.pk}))

        self.assertEqual(response.status_code, 404)

    def test_course_detail_does_not_list_resource_assigned_to_another_course(self):
        module = CourseModule.objects.create(course=self.course, title="Module")
        other_course = Course.objects.create(
            name="Other",
            slug="other",
            code="O101",
            description="Other course",
            status="published",
            visibility=Course.Visibility.PUBLIC,
        )
        resource = CourseResource.objects.create(
            course=other_course,
            module=module,
            title="Misassigned material",
            visibility=CourseResource.Visibility.PUBLIC,
            file=_pdf("misassigned.pdf"),
        )

        response = self.client.get(reverse("courses:detail", kwargs={"slug": self.course.slug}))

        self.assertNotContains(response, resource.title)

    def test_resource_clean_rejects_module_from_another_course(self):
        module = CourseModule.objects.create(course=self.course, title="Module")
        other_course = Course.objects.create(
            name="Other",
            slug="other",
            code="O101",
            description="Other course",
            status="published",
            visibility=Course.Visibility.PUBLIC,
        )
        resource = CourseResource(
            course=other_course,
            module=module,
            title="Misassigned material",
        )

        with self.assertRaises(ValidationError) as error:
            resource.full_clean()

        self.assertIn("module", error.exception.message_dict)

    def test_hidden_module_resource_404(self):
        mod = CourseModule.objects.create(course=self.course, title="Hidden", is_visible=False)
        res = CourseResource.objects.create(
            course=self.course,
            module=mod,
            title="Hidden file",
            visibility="public",
            file=_pdf("hidden.pdf"),
        )
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

    def test_module_file_resource_has_download_link(self):
        module = CourseModule.objects.create(course=self.course, title="Week 1", is_visible=True)
        resource = CourseResource.objects.create(
            course=self.course,
            module=module,
            title="Module handout",
            visibility="public",
            file=_pdf("module-handout.pdf"),
        )
        response = self.client.get(reverse("courses:detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("courses:resource_download", kwargs={"pk": resource.pk}),
        )

    def test_module_external_resource_has_open_link(self):
        module = CourseModule.objects.create(course=self.course, title="Week 2", is_visible=True)
        CourseResource.objects.create(
            course=self.course,
            module=module,
            title="External reading",
            visibility="public",
            external_url="https://example.com/reading",
        )
        response = self.client.get(reverse("courses:detail", kwargs={"slug": self.course.slug}))
        self.assertContains(response, 'href="https://example.com/reading"')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ResourceApiDownloadUrlTests(TestCase):
    def test_resource_api_returns_protected_download_url(self):
        resource = Resource.objects.create(
            title="Public resource",
            slug="public-resource",
            visibility=Resource.Visibility.PUBLIC,
            file=_pdf("public-resource.pdf"),
        )
        response = self.client.get(reverse("api:resource-detail", kwargs={"slug": resource.slug}))
        self.assertEqual(response.status_code, 200)
        path = reverse("resources:download", kwargs={"slug": resource.slug})
        self.assertTrue(response.json()["file"].endswith(path))
        self.assertNotIn("/media/", response.json()["file"])
