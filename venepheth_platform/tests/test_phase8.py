"""
Phase 8 test suite: Teaching, Events, Resources, Notifications, HTML emails, and Bulk Actions.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.notifications.models import Notification
from apps.resources.models import Resource, ResourceCategory
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

    # ── Events ───────────────────────────────────────────────────────────────

    def test_events_list_and_detail(self):
        """Events list and detail return 200."""
        now = timezone.now()
        event = Event.objects.create(
            title="Macroeconomics Symposium 2026",
            slug="macroeconomics-symposium-2026",
            event_type=Event.EventType.CONFERENCE,
            description="Annual academic conference on regional macroeconomic developments.",
            location="Vientiane National Convention Hall",
            start_time=now + timedelta(days=5),
            status="published",
        )

        list_url = reverse("events:list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.title)

        detail_url = reverse("events:detail", kwargs={"slug": event.slug})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, event.title)
        self.assertContains(detail_response, "Vientiane National Convention Hall")

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

    # ── Notifications ────────────────────────────────────────────────────────

    def test_notifications_views_and_htmx(self):
        """Notifications listing, unread badge, and mark-as-read HTMX."""
        # Unauthenticated redirects to login
        unread_url = reverse("notifications:unread_badge")
        resp = self.client.get(unread_url)
        self.assertEqual(resp.status_code, 302)

        # Authenticate
        self.client.force_login(self.user)

        # Create notifications
        notif1 = Notification.objects.create(
            user=self.user,
            message="New course enrollment approved",
            level=Notification.Level.SUCCESS,
            is_read=False,
        )
        notif2 = Notification.objects.create(
            user=self.user,
            message="Assignment deadline approaching",
            level=Notification.Level.WARNING,
            is_read=False,
        )

        # Check badge
        resp = self.client.get(unread_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "2")

        # Check list page
        list_url = reverse("notifications:list")
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, notif1.message)
        self.assertContains(resp, notif2.message)

        # Mark single notification as read via HTMX
        mark_url = reverse("notifications:mark_read", kwargs={"pk": notif1.pk})
        resp = self.client.post(mark_url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        notif1.refresh_from_db()
        self.assertTrue(notif1.is_read)

        # Badge count should now be 1
        resp = self.client.get(unread_url)
        self.assertContains(resp, "1")

        # Mark all as read via HTMX
        mark_all_url = reverse("notifications:mark_all_read")
        resp = self.client.post(mark_all_url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        notif2.refresh_from_db()
        self.assertTrue(notif2.is_read)

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
