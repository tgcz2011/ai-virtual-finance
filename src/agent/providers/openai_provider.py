from __future__ import annotations

from typing import Any

import httpx

from src.agent.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider using httpx (mock mode for testing)."""

    SUPPORTED_MODELS: set[str] = {"gpt-4", "gpt-3.5-turbo"}

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: str = "mock-api-key",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model}. Choose from {self.SUPPORTED_MODELS}")
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"})

    def generate(self, prompt: str, context: str | None = None) -> str:
        """Generate a response using the OpenAI Chat Completion API (mock)."""
        messages: list[dict[str, Any]] = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return str(choices[0].get("message", {}).get("content", ""))
            return ""
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"OpenAI API error: {exc.response.status_code}") from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected error calling OpenAI API: {exc}") from exc

    def get_name(self) -> str:
        return f"openai-{self._model}"
