"""Tests for analytics PageView middleware + admin immutability."""

from django.test import TestCase

from apps.analytics.models import PageView


class PageViewMiddlewareTests(TestCase):
    def test_get_creates_pageview(self):
        self.client.get("/")
        self.assertEqual(PageView.objects.filter(path="/").count(), 1)

    def test_referer_tracking_does_not_store_query_or_fragment(self):
        self.client.get(
            "/",
            HTTP_REFERER="https://user:password@example.com/reset/secret?token=secret#private",
        )

        page_view = PageView.objects.get(path="/")
        self.assertEqual(page_view.referer, "https://example.com")
        self.assertNotIn("secret", page_view.referer)
        self.assertNotIn("password", page_view.referer)

    def test_auth_routes_are_not_recorded_in_page_view_analytics(self):
        token_path = "/accounts/password/reset/key/uid-secret-token/"

        self.client.get(token_path)

        self.assertFalse(PageView.objects.filter(path=token_path).exists())

    def test_infra_paths_skipped(self):
        for path in ["/metrics/", "/sitemap.xml", "/robots.txt", "/health/", "/health"]:
            self.client.get(path)
        self.assertFalse(PageView.objects.exists())

    def test_post_not_logged(self):
        self.client.post("/contact/", {})
        self.assertFalse(PageView.objects.exists())


class LockoutResponseTests(TestCase):
    def test_lockout_returns_403_and_records_event(self):
        from django.test import RequestFactory

        from apps.security.models import SecurityEvent
        from apps.security.views import lockout_response

        request = RequestFactory().post("/accounts/login/", {"username": "x@y.z"})
        response = lockout_response(request, {"username": "x@y.z"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.ACCOUNT_LOCKED).exists())

    def test_lockout_scrubs_newlines(self):
        from django.test import RequestFactory

        from apps.security.models import SecurityEvent
        from apps.security.views import lockout_response

        request = RequestFactory().post("/accounts/login/")
        lockout_response(request, {"username": "a\nb\rc"})
        event = SecurityEvent.objects.latest("timestamp")
        self.assertNotIn("\n", event.description)
        self.assertNotIn("\r", event.description)
