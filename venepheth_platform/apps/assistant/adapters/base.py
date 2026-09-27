"""
Base LLM Adapter Interface.
Defines the contract for all AI LLM providers (Gemini, Local, Mock).
Conforms to Section 50 of vision.txt (AI Adapter Pattern).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseLLMAdapter(ABC):
    """Abstract interface for LLM integrations."""

    @abstractmethod
    def generate_response(
        self,
        query: str,
        context_items: List[Dict[str, Any]],
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Synthesize answer from retrieved academic context.
        Returns:
            {
                "answer": str,
                "sources": list of source dicts,
                "provider": str,
            }
        """
        pass
