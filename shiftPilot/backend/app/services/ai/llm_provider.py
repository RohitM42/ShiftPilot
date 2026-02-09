"""
LLM provider abstraction layer.
Supports Gemini (primary/free) with interface for adding fallback providers.
"""

import json
import logging
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""
    raw_text: str
    parsed_json: Optional[dict]
    model_used: str
    success: bool
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Send prompt and expect JSON response."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using REST API (no SDK, due to protobuf conflicts)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, model_name: str = "gemini-2.0-flash", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")

    def provider_name(self) -> str:
        return f"gemini/{self.model_name}"

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = f"{self.BASE_URL}/{self.model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{system_prompt}\n\n---\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()

            data = response.json()
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw)

            return LLMResponse(
                raw_text=raw,
                parsed_json=parsed,
                model_used=self.provider_name(),
                success=True,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON: {e}")
            return LLMResponse(
                raw_text=raw if "raw" in dir() else "",
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=f"Invalid JSON from LLM: {e}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API HTTP error: {e.response.status_code} - {e.response.text}")
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=f"Gemini API error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=str(e),
            )


# TO DO: Add fallback providers (OpenAI or Anthropic) by subclassing BaseLLMProvider
# class OpenAIProvider(BaseLLMProvider): ...
# class AnthropicProvider(BaseLLMProvider): ...


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory to get the configured LLM provider.
    TO DO: Add fallback chain logic here when multiple providers are configured.
    """
    provider_name = settings.LLM_PROVIDER

    if provider_name == "gemini":
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")