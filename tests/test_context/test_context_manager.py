from __future__ import annotations

import pytest

from src.agent.context.manager import ContextEntry, ContextManager
from src.agent.context.summarizer import ContextSummarizer


class TestContextManager:
    def test_add_entry(self) -> None:
        cm = ContextManager()
        cm.add_entry("user", "Hello")
        assert len(cm._entries) == 1
        assert cm._entries[0].role == "user"
        assert cm._entries[0].content == "Hello"

    def test_get_context(self) -> None:
        cm = ContextManager()
        cm.add_entry("user", "Hello")
        cm.add_entry("assistant", "Hi there")
        context = cm.get_context()
        assert "[user] Hello" in context
        assert "[assistant] Hi there" in context

    def test_clear(self) -> None:
        cm = ContextManager()
        cm.add_entry("user", "Hello")
        cm.clear()
        assert cm._entries == []
        assert cm._summary == ""

    def test_max_entries_eviction(self) -> None:
        cm = ContextManager(max_entries=3)
        cm.add_entry("user", "1")
        cm.add_entry("user", "2")
        cm.add_entry("user", "3")
        cm.add_entry("user", "4")
        assert len(cm._entries) == 3
        assert cm._entries[0].content == "2"

    def test_max_tokens_eviction(self) -> None:
        cm = ContextManager(max_tokens=10)
        long_text = "a" * 100
        cm.add_entry("user", long_text)
        assert len(cm._entries) <= 1
        assert cm._summary != ""

    def test_summarize(self) -> None:
        cm = ContextManager(max_entries=1)
        cm.add_entry("user", "First")
        cm.add_entry("user", "Second")
        summary = cm.summarize()
        assert "First" in summary

    def test_estimate_tokens(self) -> None:
        entry = ContextEntry(role="user", content="abcd")
        assert entry.estimate_tokens() == 1


class TestContextSummarizer:
    def test_daily_summary_empty(self) -> None:
        summarizer = ContextSummarizer()
        result = summarizer.daily_summary([])
        assert result == "No activity today."

    def test_weekly_summary_empty(self) -> None:
        summarizer = ContextSummarizer()
        result = summarizer.weekly_summary([])
        assert result == "No activity this week."

    def test_trade_summary_empty(self) -> None:
        summarizer = ContextSummarizer()
        result = summarizer.trade_summary([])
        assert result == "No trades."

    def test_trade_summary_with_trades(self) -> None:
        from datetime import datetime
        from src.engine.order.models import Trade
        trades = [
            Trade(id="t1", buy_order_id="o1", sell_order_id="o2", symbol="AAPL", quantity=10, price=150.0, timestamp=datetime.utcnow()),
            Trade(id="t2", buy_order_id="o3", sell_order_id="o4", symbol="AAPL", quantity=5, price=151.0, timestamp=datetime.utcnow()),
        ]
        summarizer = ContextSummarizer()
        result = summarizer.trade_summary(trades)
        assert "Total trades: 2" in result
        assert "AAPL: 2 trades" in result
