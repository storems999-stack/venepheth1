"""
Unit tests for AI Academic Assistant.
Tests the adapter pattern and RAG retriever.
NOTE: public chat/page endpoints are PARKED (see config/urls.py) — endpoint
tests live in git history and return with the feature.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.assistant.adapters import GroundedFallbackAdapter, get_llm_adapter
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
