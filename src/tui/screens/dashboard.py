from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class DashboardScreen(Screen[None]):
    """Dashboard screen showing system overview."""

    BINDINGS = [
        ("d", "noop", "Dashboard"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header(show_clock=True)
        with Container(id="dashboard-container"):
            with Horizontal(id="stats-row"):
                yield Static("Market: OPEN", id="market-status", classes="stat-box")
                yield Static("Active Agents: 5", id="active-agents", classes="stat-box")
                yield Static("Total Volume: 1,234,567", id="total-volume", classes="stat-box")
            yield Static("Recent Activity", id="activity-title")
            yield DataTable(id="activity-table")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize widgets on mount."""
        table: DataTable[str] = self.query_one("#activity-table", DataTable)
        table.add_columns("Time", "Event", "Details")
        table.add_rows([
            (datetime.now().strftime("%H:%M:%S"), "Market Open", "Session started"),
            (datetime.now().strftime("%H:%M:%S"), "Agent Join", "AlphaTrader-01"),
            (datetime.now().strftime("%H:%M:%S"), "Trade", "BUY 100 AAPL @ 150.00"),
        ])

    def action_noop(self) -> None:
        """No-op action for dashboard binding."""
