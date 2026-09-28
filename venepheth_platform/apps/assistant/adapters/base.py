"""
Base LLM Adapter Interface.
Defines the contract for all AI LLM providers (Gemini, Local, Mock).
Conforms to Section 50 of vision.txt (AI Adapter Pattern).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMAdapter(ABC):
    """Abstract interface for LLM integrations."""

    @abstractmethod
    def generate_response(
        self,
        query: str,
        context_items: list[dict[str, Any]],
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Synthesize answer from retrieved academic context.
        Returns:
            {
                "answer": str,
                "sources": list of source dicts,
                "provider": str,
            }
        """
