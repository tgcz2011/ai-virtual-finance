from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextEntry:
    """A single context entry."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def estimate_tokens(self) -> int:
        """Rough token estimation: ~4 chars per token."""
        return max(1, len(self.content) // 4)


class ContextManager:
    """Manages conversation context with sliding window and auto-summarization."""

    def __init__(self, max_tokens: int = 4000, max_entries: int = 100) -> None:
        self._max_tokens = max_tokens
        self._max_entries = max_entries
        self._entries: list[ContextEntry] = []
        self._summary: str = ""

    def add_entry(self, role: str, content: str) -> None:
        """Add a new context entry."""
        entry = ContextEntry(role=role, content=content)
        self._entries.append(entry)

        if len(self._entries) > self._max_entries:
            self._evict_oldest()

        while self._total_tokens() > self._max_tokens and self._entries:
            self._evict_oldest()

    def _total_tokens(self) -> int:
        summary_tokens = len(self._summary) // 4 if self._summary else 0
        entries_tokens = sum(e.estimate_tokens() for e in self._entries)
        return summary_tokens + entries_tokens

    def _evict_oldest(self) -> None:
        if not self._entries:
            return
        oldest = self._entries.pop(0)
        snippet = f"[{oldest.role}] {oldest.content[:100]}"
        if self._summary:
            self._summary += f"\n{snippet}"
        else:
            self._summary = snippet

    def get_context(self) -> str:
        """Return the full context as a string."""
        parts: list[str] = []
        if self._summary:
            parts.append(f"Summary:\n{self._summary}")
        for entry in self._entries:
            parts.append(f"[{entry.role}] {entry.content}")
        return "\n".join(parts)

    def summarize(self) -> str:
        """Return the current summary."""
        return self._summary

    def clear(self) -> None:
        """Clear all entries and summary."""
        self._entries.clear()
        self._summary = ""
