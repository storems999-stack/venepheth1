"""
LLM Adapter Factory.
"""
import os
from django.conf import settings
from .base import BaseLLMAdapter
from .gemini import GeminiAdapter
from .grounded_fallback import GroundedFallbackAdapter


def get_llm_adapter() -> BaseLLMAdapter:
    """Returns configured LLM adapter."""
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        return GeminiAdapter(api_key=api_key)
    return GroundedFallbackAdapter()
