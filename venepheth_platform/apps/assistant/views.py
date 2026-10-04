"""
AI Academic Assistant Views.
Provides the HTMX chat endpoint and standalone assistant page.
"""

import json
import logging
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from .adapters import get_llm_adapter
from .services.retriever import AcademicRetriever

logger = logging.getLogger("apps.assistant")

# Tiered quotas: logged-in members are keyed by account (isolated from each
# other and from guests); anonymous guests share the IP-based pool.
ASSISTANT_ANON_RATES = ("10/m", "100/d")
ASSISTANT_USER_RATES = ("30/m", "300/d")


def assistant_quota(view_func):
    """Apply tiered rate limits to the chat endpoint.

    Members (authenticated): 30/min + 300/day, keyed by user id.
    Guests (anonymous): 10/min + 100/day, keyed by IP.
    Exceeding the limit returns the global JSON 429 (RATELIMIT_VIEW).
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated:
            key, rates = "user", ASSISTANT_USER_RATES
        else:
            key, rates = "ip", ASSISTANT_ANON_RATES
        handler = view_func
        for rate in rates:
            handler = ratelimit(key=key, rate=rate, method="POST", block=True)(handler)
        return handler(request, *args, **kwargs)

    return _wrapped


@require_GET
def assistant_page(request):
    """Standalone AI Academic Assistant page."""
    is_member = request.user.is_authenticated
    rates = ASSISTANT_USER_RATES if is_member else ASSISTANT_ANON_RATES
    language = "lo" if get_language() == "lo" else "en"
    context = {
        "meta_title": "AI Academic Assistant",
        "quota_note": f"{rates[0]} · {rates[1]} ({'member' if is_member else 'guest'})",
        "suggested_prompts": [
            prompt[language]
            for prompt in [
                {"en": "When are office hours?", "lo": "ເວລາຮັບນັກສຶກສາແມ່ນເວລາໃດ?"},
                {"en": "What courses are offered?", "lo": "ມີວິຊາຮຽນຫຍັງແດ່?"},
                {"en": "Show me publications on Business Management", "lo": "ສິ່ງຕີພິມດ້ານການຈັດການທຸລະກິດ"},
                {"en": "Research projects on sustainable development", "lo": "ໂຄງການຄົ້ນຄ້ວາດ້ານການພັດທະນາຍືນຍົງ"},
                {"en": "Latest blog articles", "lo": "ບົດຄວາມລ່າສຸດ"},
            ]
        ],
    }
    return render(request, "assistant/chat.html", context)


@csrf_protect
@assistant_quota
@require_POST
def assistant_chat(request):
    """HTMX / JSON chat endpoint. Returns AI-synthesized academic answer.

    Anti-bot (zero-cost): hidden honeypot field + minimum fill-time check.
    Bots that fill the honeypot or answer instantly are logged + rejected.
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, KeyError, UnicodeDecodeError):
        body = {}
    # Any valid JSON parses — a list/str/int has no .get(), and a non-string
    # query has no .strip(). Without this guard the endpoint 500s on
    # unauthenticated input like `[1,2,3]` or `{"query": 123}`.
    if not isinstance(body, dict):
        body = {}

    raw_query = body.get("query", "")
    query = raw_query.strip() if isinstance(raw_query, str) else ""
    language = body.get("language", get_language() or "en")
    language = language if language in ("en", "lo") else "en"

    # ── Anti-bot: honeypot (real users never fill it — input is display:none)
    honeypot = body.get("website_url_hp", "") or body.get("website", "") or body.get("company_hp", "")
    if isinstance(honeypot, str) and honeypot.strip():
        _log_bot(request, "honeypot_filled")
        return JsonResponse(
            {"error": "Request rejected. Please try again.", "answer": "", "sources": []},
            status=400,
        )

    # ── Anti-bot: minimum fill time (humans need ≥2s to read + type)
    try:
        loaded_at = int(body.get("loaded_at") or 0)
    except (TypeError, ValueError):
        loaded_at = 0
    if loaded_at:
        import time

        elapsed_ms = int(time.time() * 1000) - loaded_at
        if elapsed_ms < 2000:
            _log_bot(request, f"too_fast_{elapsed_ms}ms")
            return JsonResponse(
                {"error": "Please wait a moment and try again.", "answer": "", "sources": []},
                status=400,
            )

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


def _log_bot(request, reason: str) -> None:
    """Record bot-like chat attempts without breaking the request flow."""
    try:
        from apps.security.models import SecurityEvent

        SecurityEvent.record(
            SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
            f"Assistant anti-bot triggered: {reason}",
            request=request,
            extra={"endpoint": "assistant_chat", "reason": reason},
        )
    except Exception:
        logger.exception("Assistant anti-bot logging failed")
    logger.warning("Assistant bot blocked | reason=%s", reason)
