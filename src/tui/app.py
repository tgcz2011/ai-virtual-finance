from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from src.tui.screens.agents import AgentsScreen
from src.tui.screens.dashboard import DashboardScreen
from src.tui.screens.leaderboard import LeaderboardScreen
from src.tui.screens.trading import TradingScreen


class AVFApp(App[None]):
    """Main TUI application for AI Virtual Finance."""

    CSS_PATH = "css/app.tcss"
    TITLE = "AI Virtual Finance"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "switch_screen('dashboard')", "Dashboard"),
        ("t", "switch_screen('trading')", "Trading"),
        ("a", "switch_screen('agents')", "Agents"),
        ("l", "switch_screen('leaderboard')", "Leaderboard"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "trading": TradingScreen,
        "agents": AgentsScreen,
        "leaderboard": LeaderboardScreen,
    }

    def compose(self) -> ComposeResult:
        """Compose the main app layout."""
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        """Push the dashboard screen on mount."""
        self.push_screen("dashboard")
