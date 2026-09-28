"""Unit and integration tests for Contact form, anti-spam honeypot, and notifications."""

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from apps.contact.forms import ContactForm
from apps.contact.models import ContactMessage


class ContactTests(TestCase):
    """Test contact form rendering, submissions, honeypot protection, and email."""

    def setUp(self):
        self.client = Client()
        self.contact_url = reverse("contact:form")
        cache.clear()

    def _valid_data(self, **overrides):
        data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "organization": "National University",
            "subject": "Research Collaboration",
            "message": "I would like to discuss a collaborative research project.",
            "website_url_hp": "",
        }
        data.update(overrides)
        return data

    def test_contact_page_get_ok(self):
        """Contact page GET returns 200."""
        response = self.client.get(self.contact_url)
        self.assertEqual(response.status_code, 200)

    def test_contact_page_has_form(self):
        """Contact page renders the form with honeypot field."""
        response = self.client.get(self.contact_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context.get("form"), ContactForm)
        # Honeypot field should be in the page (hidden)
        self.assertContains(response, "website_url_hp")

    def test_valid_submission_creates_db_record(self):
        """Legitimate submission creates a NEW ContactMessage."""
        response = self.client.post(self.contact_url, self._valid_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("contact:success"))

        msg = ContactMessage.objects.first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.name, "Jane Doe")
        self.assertEqual(msg.email, "jane@example.com")
        self.assertEqual(msg.status, ContactMessage.Status.NEW)

    def test_valid_submission_sends_email(self):
        """Legitimate submission dispatches a notification email."""
        self.client.post(self.contact_url, self._valid_data())
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Research Collaboration", email.subject)
        self.assertIn("Jane Doe", email.body)
        self.assertIn("jane@example.com", email.body)

    def test_valid_submission_htmx_returns_success_partial(self):
        """HTMX submission returns 200 with inline success content."""
        data = self._valid_data(name="Alex Smith", email="alex@example.com", subject="Lecture")
        response = self.client.post(self.contact_url, data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        # HTMX should return success snippet, not redirect
        self.assertNotEqual(response.status_code, 302)
        # Success partial contains a check-circle icon and success message
        self.assertContains(response, "Message Sent Successfully")
        self.assertTrue(ContactMessage.objects.filter(name="Alex Smith").exists())

    def test_honeypot_marks_as_spam(self):
        """Bot filling the honeypot is saved as SPAM."""
        data = self._valid_data(
            name="Spam Bot 3000",
            email="spambot@spamdomain.xyz",
            subject="Buy Backlinks",
            message="Rank #1 on Google!",
            website_url_hp="http://spammy-link.xyz",
        )
        response = self.client.post(self.contact_url, data)
        self.assertEqual(response.status_code, 302)

        msg = ContactMessage.objects.filter(email="spambot@spamdomain.xyz").first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.status, ContactMessage.Status.SPAM)

    def test_honeypot_does_not_send_email(self):
        """Spam submissions must NOT trigger admin email notification."""
        data = self._valid_data(
            name="Evil Bot",
            email="evil@spam.xyz",
            subject="SEO Offer",
            message="Cheap links.",
            website_url_hp="http://evil.xyz",
        )
        self.client.post(self.contact_url, data)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_required_fields_no_db_record(self):
        """Submission with empty required fields fails and saves nothing."""
        data = {
            "name": "",
            "email": "not-an-email",
            "subject": "",
            "message": "",
            "website_url_hp": "",
        }
        response = self.client.post(self.contact_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactMessage.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_success_page(self):
        """The success page returns 200."""
        response = self.client.get(reverse("contact:success"))
        self.assertEqual(response.status_code, 200)
