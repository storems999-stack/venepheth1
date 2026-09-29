"""
Unit tests for AI Academic Assistant.
Tests the adapter pattern, RAG retriever, Knowledge Box, and anti-bot guards.
"""

import json
import time
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.assistant.adapters import GroundedFallbackAdapter, get_llm_adapter
from apps.assistant.adapters.base import BaseLLMAdapter


class _FrozenTime:
    """Minimal stand-in for the `time` module with a pinned clock."""

    def __init__(self, now: float):
        self._now = now

    def time(self) -> float:
        return self._now

    def __getattr__(self, name):
        return getattr(self._real_time, name)

    _real_time = time


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


@override_settings(RATELIMIT_ENABLE=False)
class TestAssistantChatAntiBot(TestCase):
    """Endpoint guards: honeypot + minimum fill-time + validation."""

    def _post(self, payload):
        return self.client.post("/assistant/chat/", data=json.dumps(payload), content_type="application/json")

    def _old_ts(self):
        return int(time.time() * 1000) - 10_000

    def test_page_renders(self):
        resp = self.client.get("/assistant/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AI Academic Assistant")

    def test_widget_included_on_homepage(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ai-assistant-widget")

    def test_normal_query_200(self):
        resp = self._post({"query": "What courses are offered?", "loaded_at": self._old_ts()})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertTrue(data["answer"])

    def test_honeypot_blocked_and_logged(self):
        from apps.security.models import SecurityEvent

        before = SecurityEvent.objects.count()
        resp = self._post({"query": "spam", "website_url_hp": "bot-filled", "loaded_at": self._old_ts()})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SecurityEvent.objects.count(), before + 1)

    def test_too_fast_blocked(self):
        resp = self._post({"query": "fast bot", "loaded_at": int(time.time() * 1000)})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("wait a moment", resp.json()["error"])

    def test_missing_loaded_at_still_allowed(self):
        """Old cached JS without loaded_at must not break."""
        resp = self._post({"query": "hello without timestamp"})
        self.assertEqual(resp.status_code, 200)

    def test_empty_query_400(self):
        resp = self._post({"query": "  ", "loaded_at": self._old_ts()})
        self.assertEqual(resp.status_code, 400)

    def test_long_query_400(self):
        resp = self._post({"query": "x" * 501, "loaded_at": self._old_ts()})
        self.assertEqual(resp.status_code, 400)


class TestAssistantQuota(TestCase):
    """Tiered quota: per-account buckets for members, per-IP for guests."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        # django-ratelimit buckets are wall-clock aligned (_get_window uses
        # time.time()), so a test whose requests straddle a window boundary
        # sees a fresh counter and fails intermittently. Pin the clock to the
        # middle of a window so every request in the test shares one bucket.
        from django_ratelimit import core as rl_core

        original_time = rl_core.time
        rl_core.time = _FrozenTime(1_700_000_030.0)
        self.addCleanup(setattr, rl_core, "time", original_time)

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def _post(self, query="quota probe"):
        import json
        import time

        return self.client.post(
            "/assistant/chat/",
            data=json.dumps({"query": query, "loaded_at": int(time.time() * 1000) - 10_000}),
            content_type="application/json",
        )

    def _make_user(self, email):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(email=email, password="SecurePass123!")

    def test_guest_limited_to_10_per_minute(self):
        for _ in range(10):
            self.assertEqual(self._post().status_code, 200)
        resp = self._post()
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json(), {"error": "Too many requests. Please try again later."})

    def test_member_isolated_from_guest_quota(self):
        """A logged-in member is keyed by account, not by the shared IP pool."""
        for _ in range(10):
            self.assertEqual(self._post().status_code, 200)
        self.assertEqual(self._post().status_code, 429)  # guest IP pool exhausted
        self.client.force_login(self._make_user("member-quota@test.com"))
        self.assertEqual(self._post().status_code, 200)

    def test_member_gets_30_per_minute(self):
        self.client.force_login(self._make_user("member30@test.com"))
        for _ in range(30):
            self.assertEqual(self._post().status_code, 200)
        self.assertEqual(self._post().status_code, 429)

    def test_quota_note_differs_by_auth(self):
        resp = self.client.get("/assistant/")
        self.assertContains(resp, "10/m")
        self.client.force_login(self._make_user("member-note@test.com"))
        resp = self.client.get("/assistant/")
        self.assertContains(resp, "30/m")


class TestAssistantDashboard(TestCase):
    """Staff dashboard shows AI Knowledge Box health (read-only)."""

    def _staff_client(self):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_user(email="studio@test.com", password="SecurePass123!", is_staff=True)
        self.client.force_login(staff)

    def test_staff_sees_knowledge_panel(self):
        from django.urls import reverse

        self._staff_client()
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Knowledge Box")
        self.assertContains(resp, "AI Assistant Health")

    def test_anonymous_redirected_to_login(self):
        from django.urls import reverse

        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 302)


class TestKnowledgeBox(TestCase):
    """KnowledgeDocument is prioritized by the retriever."""

    def test_knowledge_doc_ranked_first(self):
        from apps.assistant.models import KnowledgeDocument
        from apps.assistant.services.retriever import AcademicRetriever

        KnowledgeDocument.objects.create(
            title="Zxq Office FAQ",
            content="Zxq office hours Monday 9am knowledge box entry",
            tags="zxq-office",
        )
        results = AcademicRetriever.retrieve("Zxq office Monday", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0]["type"], "Knowledge Base")
        self.assertIn("Zxq Office FAQ", results[0]["title"])

    def test_inactive_doc_ignored(self):
        from apps.assistant.models import KnowledgeDocument
        from apps.assistant.services.retriever import AcademicRetriever

        KnowledgeDocument.objects.create(
            title="Qwx Hidden Doc",
            content="Qwx hidden content never shown",
            is_active=False,
        )
        results = AcademicRetriever.retrieve("Qwx hidden", limit=5)
        self.assertFalse([r for r in results if "Qwx Hidden" in r.get("title", "")])

    def test_library_resource_retrieved(self):
        from apps.assistant.services.retriever import AcademicRetriever
        from apps.resources.models import Resource

        Resource.objects.create(
            title="Wqv Test Handbook",
            slug="wqv-test-handbook",
            description="Wqv handbook for library RAG",
            visibility=Resource.Visibility.PUBLIC,
        )
        results = AcademicRetriever.retrieve("Wqv handbook", limit=8)
        self.assertTrue([r for r in results if r["type"] == "Library Resource"])


class TestPdfExtraction(TestCase):
    """PDF uploads are auto-indexed via pypdf (graceful without it)."""

    def _make_pdf_bytes(self, text="Hello PDF knowledge"):
        """Build a minimal valid one-page PDF (offsets computed dynamically)."""
        content = f"BT /F1 12 Tf 10 10 Td ({text}) Tj ET".encode("latin-1")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = []
        for i, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf += b"%d 0 obj\n" % i + body + b"\nendobj\n"
        xref_pos = len(pdf)
        pdf += b"xref\n0 %d\n" % (len(objects) + 1)
        pdf += b"0000000000 65535 f \n"
        for off in offsets:
            pdf += b"%010d 00000 n \n" % off
        pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objects) + 1, xref_pos)
        return bytes(pdf)

    def test_extract_pdf_text(self):
        import io

        from apps.assistant.models import extract_pdf_text

        pdf_bytes = self._make_pdf_bytes()
        self.assertIn("Hello PDF", extract_pdf_text(io.BytesIO(pdf_bytes)))

    def test_pdf_save_auto_extracts(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.assistant.models import KnowledgeDocument

        pdf_bytes = self._make_pdf_bytes("SavePath extraction check")
        doc = KnowledgeDocument(title="Pdf Save Doc")
        doc.file.save("save-check.pdf", SimpleUploadedFile("save-check.pdf", pdf_bytes), save=False)
        doc.save()
        self.assertIn("SavePath", doc.file_text)

    def test_corrupt_pdf_does_not_crash(self):
        import io

        from apps.assistant.models import extract_pdf_text

        self.assertEqual(extract_pdf_text(io.BytesIO(b"not a pdf")), "")


class TestSettings(TestCase):
    def test_gemini_api_key_setting_exists(self):
        from django.conf import settings

        self.assertTrue(hasattr(settings, "GEMINI_API_KEY"))

    def test_adapter_factory_uses_settings_key(self):
        from django.test import override_settings

        from apps.assistant.adapters import get_llm_adapter
        from apps.assistant.adapters.grounded_fallback import GroundedFallbackAdapter

        with override_settings(GEMINI_API_KEY=""):
            self.assertIsInstance(get_llm_adapter(), GroundedFallbackAdapter)


class TestReindexCommand(TestCase):
    def test_reindex_backfills_empty_file_text(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.management import call_command

        from apps.assistant.models import KnowledgeDocument

        doc = KnowledgeDocument(title="Reindex Me", file_text="")
        doc.file.save(
            "reindex.txt",
            SimpleUploadedFile("reindex.txt", b"Reindex backfill content"),
            save=False,
        )
        doc.save()
        # Simulate a doc uploaded before extraction existed.
        KnowledgeDocument.objects.filter(pk=doc.pk).update(file_text="")
        call_command("reindex_knowledge")
        doc.refresh_from_db()
        self.assertIn("Reindex backfill", doc.file_text)

    def test_extract_file_text_unsupported_returns_none(self):
        from apps.assistant.models import KnowledgeDocument

        doc = KnowledgeDocument(title="No file here")
        self.assertEqual(doc.extract_file_text(), "")


class TestKnowledgeInGlobalSearch(TestCase):
    """Knowledge Box entries appear on the global /search/ page."""

    def test_search_finds_active_knowledge_doc(self):
        from apps.assistant.models import KnowledgeDocument

        KnowledgeDocument.objects.create(
            title="Vqw Searchable Guide",
            summary="Vqw unique summary for search",
            content="Vqw body text",
            is_active=True,
        )
        resp = self.client.get("/search/", {"q": "Vqw"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Vqw Searchable Guide")
        self.assertContains(resp, "Knowledge Base")

    def test_search_hides_inactive_knowledge_doc(self):
        from apps.assistant.models import KnowledgeDocument

        KnowledgeDocument.objects.create(
            title="Xzx Hidden Guide",
            content="Xzx body text",
            is_active=False,
        )
        resp = self.client.get("/search/", {"q": "Xzx"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Xzx Hidden Guide")


class TestSeedFaqsMigration(TestCase):
    """0002 migration seeds starter FAQs idempotently."""

    def test_seed_function_is_idempotent(self):
        import importlib

        from django.apps import apps as django_apps

        mod = importlib.import_module("apps.assistant.migrations.0002_seed_faqs")
        seed = mod.seed_faqs
        seed(django_apps, None)
        from apps.assistant.models import KnowledgeDocument

        count_first = KnowledgeDocument.objects.filter(slug__in=[f["slug"] for f in mod.SEED_FAQS]).count()
        self.assertEqual(count_first, len(mod.SEED_FAQS))
        # Second run must not duplicate or overwrite admin edits.
        seed(django_apps, None)
        count_second = KnowledgeDocument.objects.filter(slug__in=[f["slug"] for f in mod.SEED_FAQS]).count()
        self.assertEqual(count_second, len(mod.SEED_FAQS))
        # Seeded entries are retrievable by the assistant.
        from apps.assistant.services.retriever import AcademicRetriever

        results = AcademicRetriever.retrieve("office hours Teaching page", limit=8)
        self.assertTrue([r for r in results if r["type"] == "Knowledge Base"])
