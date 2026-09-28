"""Rate limiting tests (Vision §14, §21)."""

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse


class RateLimitTests(TestCase):
    """Verify django-ratelimit decorators block excessive requests."""

    def setUp(self):
        self.client = Client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_contact_form_blocks_after_five_posts_per_minute(self):
        """Contact form POST should return 429 on the 6th request."""
        url = reverse("contact:form")
        for _ in range(5):
            response = self.client.post(url, {})
            self.assertIn(response.status_code, [200, 302])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 429)

    def test_search_results_blocks_after_ten_gets_per_minute(self):
        """Search results should return 429 on the 11th GET request."""
        url = reverse("search:results")
        for _ in range(10):
            response = self.client.get(url, {"q": "Economics"})
            self.assertEqual(response.status_code, 200)
        response = self.client.get(url, {"q": "Economics"})
        self.assertEqual(response.status_code, 429)

    def test_assistant_chat_blocks_after_ten_posts_per_minute(self):
        """Assistant chat should return 429 on the 11th POST request."""
        url = reverse("assistant:api_chat")
        for _ in range(10):
            response = self.client.post(url, {"query": "hello"}, content_type="application/json")
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {"query": "hello"}, content_type="application/json")
        self.assertEqual(response.status_code, 429)

    def test_rate_limited_view_returns_json_429(self):
        """The ratelimited view should return JSON with 429."""
        url = reverse("contact:form")
        for _ in range(6):
            response = self.client.post(url, {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "Too many requests. Please try again later."})

    def test_api_viewset_blocks_after_hundred_gets_per_minute(self):
        """API ViewSets should be rate-limited by IP."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="ratelimit@test.com",
            password="SecurePass123!",
            is_staff=True,
        )
        self.client.force_login(user)
        url = reverse("api:profile-list")
        for _ in range(100):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "Too many requests. Please try again later."})
