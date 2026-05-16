from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.context.manager import ContextEntry as ManagerContextEntry
    from src.engine.order.models import Trade

    ContextEntry = ManagerContextEntry


class ContextSummarizer:
    """Summarizes context entries and trades."""

    def daily_summary(self, entries: list[ContextEntry]) -> str:
        """Generate a daily summary from context entries."""
        if not entries:
            return "No activity today."

        today = datetime.utcnow().date()
        today_entries = [e for e in entries if e.timestamp.date() == today]

        if not today_entries:
            return "No activity today."

        roles: dict[str, int] = {}
        for e in today_entries:
            roles[e.role] = roles.get(e.role, 0) + 1

        lines = [f"Daily Summary ({today.isoformat()}):", f"Total entries: {len(today_entries)}"]
        for role, count in sorted(roles.items()):
            lines.append(f"  {role}: {count}")

        return "\n".join(lines)

    def weekly_summary(self, entries: list[ContextEntry]) -> str:
        """Generate a weekly summary from context entries."""
        if not entries:
            return "No activity this week."

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        week_entries = [e for e in entries if week_ago <= e.timestamp <= now]

        if not week_entries:
            return "No activity this week."

        daily_counts: dict[str, int] = {}
        for e in week_entries:
            day = e.timestamp.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1

        lines = ["Weekly Summary:", f"Total entries: {len(week_entries)}"]
        for day, count in sorted(daily_counts.items()):
            lines.append(f"  {day}: {count} entries")

        return "\n".join(lines)

    def trade_summary(self, trades: list[Trade]) -> str:
        """Generate a summary from a list of trades."""
        if not trades:
            return "No trades."

        total_volume = sum(t.quantity for t in trades)
        total_notional = sum(t.quantity * t.price for t in trades)
        avg_price = total_notional / total_volume if total_volume > 0 else 0.0

        symbols: dict[str, int] = {}
        for t in trades:
            symbols[t.symbol] = symbols.get(t.symbol, 0) + 1

        lines = [
            "Trade Summary:",
            f"Total trades: {len(trades)}",
            f"Total volume: {total_volume:.2f}",
            f"Total notional: {total_notional:.2f}",
            f"Average price: {avg_price:.2f}",
            "Symbols:",
        ]
        for sym, count in sorted(symbols.items()):
            lines.append(f"  {sym}: {count} trades")

        return "\n".join(lines)
