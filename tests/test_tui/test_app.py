from __future__ import annotations

import pytest
from textual.pilot import Pilot

from src.tui.app import AVFApp
from src.tui.screens.agents import AgentsScreen
from src.tui.screens.dashboard import DashboardScreen
from src.tui.screens.leaderboard import LeaderboardScreen
from src.tui.screens.trading import TradingScreen


@pytest.mark.asyncio
async def test_app_title() -> None:
    """Test that the app has the correct title."""
    app = AVFApp()
    async with app.run_test() as pilot:
        assert app.title == "AI Virtual Finance"
        await pilot.pause()


@pytest.mark.asyncio
async def test_dashboard_screen_on_mount() -> None:
    """Test that dashboard screen is shown on mount."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_switch_to_trading_screen() -> None:
    """Test switching to trading screen."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        assert isinstance(app.screen, TradingScreen)


@pytest.mark.asyncio
async def test_switch_to_agents_screen() -> None:
    """Test switching to agents screen."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, AgentsScreen)


@pytest.mark.asyncio
async def test_switch_to_leaderboard_screen() -> None:
    """Test switching to leaderboard screen."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, LeaderboardScreen)


@pytest.mark.asyncio
async def test_switch_back_to_dashboard() -> None:
    """Test switching back to dashboard screen."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_header_exists() -> None:
    """Test that Header widget exists."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        header = app.query_one("Header")
        assert header is not None


@pytest.mark.asyncio
async def test_footer_exists() -> None:
    """Test that Footer widget exists."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one("Footer")
        assert footer is not None
