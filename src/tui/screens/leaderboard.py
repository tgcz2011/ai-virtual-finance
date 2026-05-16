from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header


class LeaderboardScreen(Screen[None]):
    """Leaderboard screen showing agent rankings."""

    BINDINGS = [
        ("l", "noop", "Leaderboard"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the leaderboard layout."""
        yield Header(show_clock=True)
        with Container(id="leaderboard-container"):
            yield DataTable(id="leaderboard-table")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize widgets on mount."""
        table: DataTable[str] = self.query_one("#leaderboard-table", DataTable)
        table.add_columns("Rank", "Agent", "Total Return", "Sharpe", "Max Drawdown", "Win Rate")
        table.add_rows([
            ("1", "DeltaDealer", "+7.8%", "1.85", "-2.1%", "62%"),
            ("2", "AlphaTrader", "+5.2%", "1.52", "-3.5%", "58%"),
            ("3", "BetaBot", "+3.1%", "1.21", "-4.2%", "55%"),
            ("4", "GammaGuru", "-0.5%", "0.95", "-5.8%", "48%"),
        ])

    def action_noop(self) -> None:
        """No-op action for leaderboard binding."""
