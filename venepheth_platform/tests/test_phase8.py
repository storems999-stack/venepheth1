"""
Phase 8 test suite: Teaching, Events, Resources, Notifications, HTML emails, and Bulk Actions.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.resources.models import Resource, ResourceCategory
from apps.teaching.admin import StudentAnnouncementAdmin
from apps.teaching.models import OfficeHours, StudentAnnouncement, TeachingPhilosophy

User = get_user_model()


class Phase8Tests(TestCase):
    """Verify Phase 8 features and endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
        )
        cache.clear()

    # ── Teaching ─────────────────────────────────────────────────────────────

    def test_teaching_overview(self):
        """Teaching overview view displays office hours, philosophy, and announcements."""
        OfficeHours.objects.create(
            day=OfficeHours.Day.MON,
            start_time="09:00",
            end_time="11:00",
            location="Room 304, Faculty of Economics",
            is_active=True,
        )
        TeachingPhilosophy.objects.create(
            headline="Student-Centered Inquiry",
            body="Encouraging active debate, rigorous empirical methods, and ethical leadership.",
            is_active=True,
        )
        StudentAnnouncement.objects.create(
            title="Midterm Exam Schedule",
            body="Midterm exams will be conducted next week.",
            status="published",
        )

        url = reverse("teaching:overview")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Room 304")
        self.assertContains(response, "Student-Centered Inquiry")
        self.assertContains(response, "Midterm Exam Schedule")

    def test_teaching_page_csrf_token_works_for_each_visitor(self):
        """Each visitor must get a CSRF token that matches their own cookie."""
        import re

        visitors = [Client(enforce_csrf_checks=True), Client(enforce_csrf_checks=True)]
        for visitor in visitors:
            response = visitor.get(reverse("teaching:overview"))
            self.assertEqual(response.status_code, 200)
            token = re.search(r'"X-CSRFToken": "([^"]+)"', response.content.decode())
            self.assertIsNotNone(token)

            post_response = visitor.post(
                reverse("contact:form"),
                {"csrfmiddlewaretoken": token.group(1)},
            )
            self.assertNotEqual(post_response.status_code, 403)

    def test_cached_course_list_does_not_replay_authenticated_navigation(self):
        """The shared page cache must vary by session cookie."""
        cache.clear()
        self.client.force_login(self.user)
        self.client.get(reverse("courses:list"))
        authenticated_response = self.client.get(reverse("courses:list"))
        self.assertContains(authenticated_response, "Dashboard")

        anonymous_client = Client()
        anonymous_client.get(reverse("courses:list"))
        anonymous_response = anonymous_client.get(reverse("courses:list"))
        self.assertContains(anonymous_response, "Login")
        self.assertNotContains(anonymous_response, "Dashboard")

    def test_cached_list_pages_keep_csrf_valid_for_new_visitors(self):
        import re

        for url in (reverse("courses:list"), reverse("blog:list"), reverse("research:list")):
            with self.subTest(url=url):
                cache.clear()
                for visitor in (Client(enforce_csrf_checks=True), Client(enforce_csrf_checks=True)):
                    response = visitor.get(url)
                    self.assertEqual(response.status_code, 200)
                    token = re.search(r'"X-CSRFToken": "([^"]+)"', response.content.decode())
                    self.assertIsNotNone(token)
                    post_response = visitor.post(
                        reverse("contact:form"),
                        {"csrfmiddlewaretoken": token.group(1)},
                    )
                    self.assertNotEqual(post_response.status_code, 403)

    # ── Resources ────────────────────────────────────────────────────────────

    def test_resources_list_and_detail(self):
        """Resources list and detail return 200."""
        cat = ResourceCategory.objects.create(name="Lecture Notes", slug="lecture-notes")
        res = Resource.objects.create(
            title="Microeconomics Syllabus and Readings",
            slug="microeconomics-syllabus-and-readings",
            description="Curated reading list for advanced microeconomic analysis.",
            category=cat,
            resource_type=Resource.ResourceType.PDF,
            visibility=Resource.Visibility.PUBLIC,
            external_url="https://example.com/syllabus.pdf",
        )

        list_url = reverse("resources:list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, res.title)

        detail_url = reverse("resources:detail", kwargs={"slug": res.slug})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, res.title)

    # ── Contact Email & Honeypot ─────────────────────────────────────────────

    def test_contact_form_sends_html_email(self):
        """Contact form submission creates record and dispatches HTML notification email."""
        mail.outbox.clear()
        post_data = {
            "name": "Prof. Alice Smith",
            "email": "alice@university.org",
            "organization": "National University",
            "subject": "Research Collaboration Invitation",
            "message": "We would like to collaborate on the upcoming development study.",
            "website_url_hp": "",  # honeypot left empty
        }
        resp = self.client.post(reverse("contact:form"), post_data)
        self.assertEqual(resp.status_code, 302)

        # Verify email dispatched with HTML alternative
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("Research Collaboration Invitation", sent_email.subject)
        self.assertIn("Prof. Alice Smith", sent_email.body)
        self.assertTrue(any("<!DOCTYPE html>" in alt[0] for alt in sent_email.alternatives))

    def test_contact_form_honeypot_spam_trap(self):
        """Filled honeypot field marks contact as SPAM and does not dispatch email."""
        mail.outbox.clear()
        post_data = {
            "name": "Spam Bot",
            "email": "bot@spam.com",
            "subject": "Buy crypto now",
            "message": "Spam spam spam",
            "website_url_hp": "im_a_bot",  # bot fills honeypot
        }
        resp = self.client.post(reverse("contact:form"), post_data)
        self.assertEqual(resp.status_code, 302)
        # Should NOT send email
        self.assertEqual(len(mail.outbox), 0)


class StudentAnnouncementPublicationTests(TestCase):
    def setUp(self):
        self.announcement = StudentAnnouncement.objects.create(
            title="Upcoming seminar",
            body="Seminar details.",
        )
        self.model_admin = StudentAnnouncementAdmin(StudentAnnouncement, admin.site)

    def test_bulk_publish_sets_publication_timestamp(self):
        history_count_before = self.announcement.history.count()

        self.model_admin.mark_published(
            None,
            StudentAnnouncement.objects.filter(pk=self.announcement.pk),
        )

        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.status, StudentAnnouncement.Status.PUBLISHED)
        self.assertIsNotNone(self.announcement.published_at)
        self.assertEqual(self.announcement.history.count(), history_count_before + 1)

    def test_admin_form_publish_sets_publication_timestamp(self):
        self.announcement.status = StudentAnnouncement.Status.PUBLISHED
        request = RequestFactory().post("/admin/teaching/studentannouncement/")
        before_save = timezone.now()

        self.model_admin.save_model(request, self.announcement, form=None, change=True)

        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.status, StudentAnnouncement.Status.PUBLISHED)
        self.assertGreaterEqual(self.announcement.published_at, before_save)
