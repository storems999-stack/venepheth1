"""
Unit tests for Prometheus metrics endpoint.
"""

from django.test import TestCase, override_settings


class TestPrometheusMetrics(TestCase):
    """Test the /metrics/ Prometheus-compatible endpoint."""

    def test_metrics_endpoint_returns_200(self):
        """GET /metrics/ should return 200 with text/plain content type."""
        resp = self.client.get("/metrics/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Type"].startswith("text/plain"))

    def test_metrics_contains_expected_gauges(self):
        """Output should conform to Prometheus text format 0.0.4 with expected metrics."""
        resp = self.client.get("/metrics/")
        content = resp.content.decode("utf-8")

        expected_metrics = [
            "platform_uptime_seconds",
            "platform_users_total",
            "platform_active_users_total",
            "platform_articles_total",
            "platform_research_projects_total",
            "platform_publications_total",
            "platform_courses_total",
            "platform_events_total",
            "platform_scrape_timestamp_seconds",
        ]

        for metric in expected_metrics:
            with self.subTest(metric=metric):
                self.assertIn(metric, content)
                self.assertIn(f"# HELP {metric}", content)
                self.assertIn(f"# TYPE {metric} gauge", content)

    @override_settings(METRICS_TOKEN="super-secret-token")
    def test_metrics_token_auth_enforced(self):
        """When METRICS_TOKEN is set, unauthorized requests return 403."""
        # Unauthorized without token
        resp = self.client.get("/metrics/")
        self.assertEqual(resp.status_code, 403)

        # Authorized with correct token
        resp = self.client.get("/metrics/", HTTP_X_METRICS_TOKEN="super-secret-token")
        self.assertEqual(resp.status_code, 200)
