"""
AI Academic Assistant Views.
Provides the HTMX chat endpoint and standalone assistant page.
"""

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from .adapters import get_llm_adapter
from .services.retriever import AcademicRetriever

logger = logging.getLogger("apps.assistant")


@require_GET
def assistant_page(request):
    """Standalone AI Academic Assistant page."""
    context = {
        "meta_title": "AI Academic Assistant",
        "suggested_prompts": [
            {"en": "When are office hours?", "lo": "ເວລາຮັບນັກສຶກສາແມ່ນເວລາໃດ?"},
            {"en": "What courses are offered?", "lo": "ມີວິຊາຮຽນຫຍັງແດ່?"},
            {"en": "Show me publications on Business Management", "lo": "ສິ່ງຕີພິມດ້ານການຈັດການທຸລະກິດ"},
            {"en": "Research projects on sustainable development", "lo": "ໂຄງການຄົ້ນຄ້ວາດ້ານການພັດທະນາຍືນຍົງ"},
            {"en": "Latest blog articles", "lo": "ບົດຄວາມລ່າສຸດ"},
        ],
    }
    return render(request, "assistant/chat.html", context)


@csrf_protect
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
@require_POST
def assistant_chat(request):
    """HTMX / JSON chat endpoint. Returns AI-synthesized academic answer."""
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, KeyError, UnicodeDecodeError):
        body = {}

    query = body.get("query", "").strip()
    language = body.get("language", get_language() or "en")
    language = language if language in ("en", "lo") else "en"

    if not query:
        return JsonResponse(
            {"error": "Query is required.", "answer": "", "sources": []},
            status=400,
        )

    if len(query) > 500:
        return JsonResponse(
            {"error": "Query too long (max 500 chars).", "answer": "", "sources": []},
            status=400,
        )

    # Log shape, not content (queries may contain PII).
    logger.info("Assistant query received | lang=%s chars=%d", language, len(query))

    # RAG: Retrieve relevant academic context
    context_items = AcademicRetriever.retrieve(query, limit=8)

    # Generate answer through configured adapter
    adapter = get_llm_adapter()
    result = adapter.generate_response(query, context_items, language=language)

    return JsonResponse(
        {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "provider": result.get("provider", ""),
            "query": query,
        }
    )
