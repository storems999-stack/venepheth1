"""
Unit tests for AI Academic Assistant.
Tests the adapter pattern, RAG retriever, and chat API endpoint.
"""
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory
from django.urls import reverse

from apps.assistant.adapters import get_llm_adapter, GroundedFallbackAdapter
from apps.assistant.adapters.base import BaseLLMAdapter


class TestBaseLLMAdapter(TestCase):
    """Test adapter interface contract."""

    def test_base_adapter_is_abstract(self):
        """BaseLLMAdapter cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseLLMAdapter()

    def test_grounded_fallback_adapter_instantiates(self):
        """GroundedFallbackAdapter can be created without API keys."""
        adapter = GroundedFallbackAdapter()
        self.assertIsNotNone(adapter)
        self.assertIsInstance(adapter, BaseLLMAdapter)

    def test_grounded_fallback_returns_response(self):
        """GroundedFallbackAdapter.generate_response returns expected structure."""
        adapter = GroundedFallbackAdapter()
        context = [
            {"type": "course", "title": "Business Management", "description": "Core course"},
        ]
        result = adapter.generate_response("What courses are available?", context, language="en")
        self.assertIsInstance(result, dict)
        self.assertIn("answer", result)
        self.assertIn("sources", result)
        self.assertIn("provider", result)
        self.assertTrue(len(result["answer"]) > 0)
        self.assertEqual(result["provider"], "Local Academic Knowledge Engine")

    def test_grounded_fallback_lao_language(self):
        """GroundedFallbackAdapter respects Lao language parameter."""
        adapter = GroundedFallbackAdapter()
        result = adapter.generate_response("ວິຊາຮຽນ", [], language="lo")
        self.assertIn("answer", result)
        self.assertEqual(result["provider"], "Local Academic Knowledge Engine")

    def test_grounded_fallback_empty_context(self):
        """GroundedFallbackAdapter handles empty context gracefully."""
        adapter = GroundedFallbackAdapter()
        result = adapter.generate_response("Random query", [], language="en")
        self.assertIn("answer", result)
        self.assertIsInstance(result["sources"], list)


class TestGetLLMAdapter(TestCase):
    """Test the adapter factory function."""

    @patch("apps.assistant.adapters.settings")
    def test_returns_fallback_without_api_key(self, mock_settings):
        """get_llm_adapter() returns GroundedFallbackAdapter when no API key configured."""
        mock_settings.GEMINI_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        adapter = get_llm_adapter()
        self.assertIsInstance(adapter, GroundedFallbackAdapter)

    def test_get_llm_adapter_returns_adapter_instance(self):
        """get_llm_adapter() always returns a BaseLLMAdapter subclass."""
        adapter = get_llm_adapter()
        self.assertIsInstance(adapter, BaseLLMAdapter)


class TestAssistantChatEndpoint(TestCase):
    """Test the /assistant/chat/ POST endpoint."""

    def setUp(self):
        self.url = "/assistant/chat/"
        self.client.enforce_csrf_checks = False  # CSRF tested separately

    def test_post_with_valid_query_returns_200(self):
        """Valid POST to /assistant/chat/ should return 200 with answer."""
        resp = self.client.post(
            self.url,
            data=json.dumps({"query": "What courses are offered?", "language": "en"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)

    def test_post_empty_query_returns_400(self):
        """Empty query should return 400."""
        resp = self.client.post(
            self.url,
            data=json.dumps({"query": "", "language": "en"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_post_query_too_long_returns_400(self):
        """Query exceeding 500 chars should return 400."""
        resp = self.client.post(
            self.url,
            data=json.dumps({"query": "x" * 501, "language": "en"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_get_request_returns_405(self):
        """GET request to chat endpoint should return 405."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_assistant_page_loads(self):
        """GET /assistant/ should return 200."""
        resp = self.client.get("/assistant/")
        self.assertEqual(resp.status_code, 200)


class TestAcademicRetriever(TestCase):
    """Test the RAG AcademicRetriever service."""

    def test_retrieve_returns_list(self):
        """AcademicRetriever.retrieve() should return a list even with empty DB."""
        from apps.assistant.services.retriever import AcademicRetriever
        results = AcademicRetriever.retrieve("management", limit=5)
        self.assertIsInstance(results, list)

    def test_retrieve_respects_limit(self):
        """AcademicRetriever.retrieve() should not exceed the specified limit."""
        from apps.assistant.services.retriever import AcademicRetriever
        results = AcademicRetriever.retrieve("any topic", limit=3)
        self.assertLessEqual(len(results), 3)
