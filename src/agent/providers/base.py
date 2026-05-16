from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, context: str | None = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt.
            context: Optional context to include.

        Returns:
            The generated response string.
        """
        raise NotImplementedError

    @abstractmethod
    def get_name(self) -> str:
        """Return the provider name."""
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing purposes."""

    def __init__(self, response: str = "HOLD") -> None:
        self._response = response

    def generate(self, prompt: str, context: str | None = None) -> str:
        """Return a canned response."""
        return self._response

    def get_name(self) -> str:
        return "mock"
