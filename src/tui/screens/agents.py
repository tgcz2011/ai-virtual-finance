from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static


class AgentsScreen(Screen[None]):
    """Agents screen showing agent list and controls."""

    BINDINGS = [
        ("a", "noop", "Agents"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the agents layout."""
        yield Header(show_clock=True)
        with Container(id="agents-container"):
            with Horizontal(id="agents-top"):
                with Container(id="agent-list-container"):
                    yield Static("Agent List", id="agent-list-title")
                    yield DataTable(id="agent-table")
                with Container(id="agent-config-container"):
                    yield Static("Configuration", id="agent-config-title")
                    yield Static("Select an agent to view config.", id="agent-config-content")
            with Horizontal(id="agent-controls"):
                yield Button("Pause", id="pause-btn", variant="warning")
                yield Button("Resume", id="resume-btn", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize widgets on mount."""
        table: DataTable[str] = self.query_one("#agent-table", DataTable)
        table.add_columns("ID", "Name", "Strategy", "Status", "P&L")
        table.add_rows([
            ("001", "AlphaTrader", "Momentum", "ACTIVE", "+5.2%"),
            ("002", "BetaBot", "Mean Reversion", "ACTIVE", "+3.1%"),
            ("003", "GammaGuru", "Arbitrage", "PAUSED", "-0.5%"),
            ("004", "DeltaDealer", "Trend Following", "ACTIVE", "+7.8%"),
        ])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "pause-btn":
            self.notify("Agent paused", severity="warning")
        elif event.button.id == "resume-btn":
            self.notify("Agent resumed", severity="information")

    def action_noop(self) -> None:
        """No-op action for agents binding."""
