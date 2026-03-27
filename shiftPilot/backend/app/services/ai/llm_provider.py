"""
LLM provider abstraction layer.
Supports Gemini (primary/free) with interface for adding fallback providers.
"""

import json
import logging
import time as time_module
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
    MAX_RETRIES = 3

    def __init__(self, model_name: str = None, api_key: Optional[str] = None):
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
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

        raw = ""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = httpx.post(url, json=payload, timeout=30.0)

                if response.status_code == 429:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"Gemini 429 rate limit, retrying in {wait}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time_module.sleep(wait)
                    continue

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
                    raw_text=raw,
                    parsed_json=None,
                    model_used=self.provider_name(),
                    success=False,
                    error=f"Invalid JSON from LLM: {e}",
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Gemini 429 rate limit, retrying in {wait}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time_module.sleep(wait)
                    continue
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

        # Exhausted all retries on 429
        logger.error(f"Gemini rate limit exceeded after {self.MAX_RETRIES} retries")
        return LLMResponse(
            raw_text="",
            parsed_json=None,
            model_used=self.provider_name(),
            success=False,
            error="Gemini API error: 429",
        )


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter provider — OpenAI-compatible REST API with access to many free models.
    Used as a fallback when the primary provider fails or rate-limits.
    See https://openrouter.ai/docs for model list.
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_name: str = None, api_key: str = None):
        self.model_name = model_name or settings.OPENROUTER_MODEL or "mistralai/mistral-7b-instruct"
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

    def provider_name(self) -> str:
        return f"openrouter/{self.model_name}"

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        raw = ""
        try:
            response = httpx.post(self.BASE_URL, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()

            data = response.json()
            raw = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw)

            return LLMResponse(
                raw_text=raw,
                parsed_json=parsed,
                model_used=self.provider_name(),
                success=True,
            )

        except json.JSONDecodeError as e:
            logger.error(f"OpenRouter returned invalid JSON: {e}\nRaw: {raw[:500]}")
            return LLMResponse(
                raw_text=raw,
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=f"Invalid JSON from LLM: {e}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=f"OpenRouter API error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model_used=self.provider_name(),
                success=False,
                error=str(e),
            )


class FallbackProvider(BaseLLMProvider):
    """
    Tries each provider in order, returning the first successful response.
    Logs a warning when falling back.
    """

    def __init__(self, providers: list[BaseLLMProvider]):
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider")
        self._providers = providers

    def provider_name(self) -> str:
        return " -> ".join(p.provider_name() for p in self._providers)

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        last_response = None
        for provider in self._providers:
            response = provider.generate_json(system_prompt, user_prompt)
            if response.success:
                if last_response is not None:
                    logger.warning(f"Primary provider failed, used fallback: {provider.provider_name()}")
                return response
            last_response = response
            logger.warning(f"Provider {provider.provider_name()} failed: {response.error} — trying next")
        return last_response


def get_llm_provider() -> BaseLLMProvider:
    """
    Returns the configured provider with OpenRouter as fallback if key is set.
    Primary provider is determined by LLM_PROVIDER env var (default: gemini).
    """
    provider_name = settings.LLM_PROVIDER

    if provider_name == "gemini":
        primary = GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

    if settings.OPENROUTER_API_KEY:
        return FallbackProvider([primary, OpenRouterProvider()])

    return primary