from __future__ import annotations

import pytest

from src.tui.app import AVFApp
from src.tui.screens.agents import AgentsScreen
from src.tui.screens.dashboard import DashboardScreen
from src.tui.screens.leaderboard import LeaderboardScreen
from src.tui.screens.trading import TradingScreen


@pytest.mark.asyncio
async def test_dashboard_has_activity_table() -> None:
    """Test that dashboard screen has activity table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        table = screen.query_one("#activity-table")
        assert table is not None


@pytest.mark.asyncio
async def test_dashboard_has_stat_boxes() -> None:
    """Test that dashboard screen has stat boxes."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        market_status = screen.query_one("#market-status")
        active_agents = screen.query_one("#active-agents")
        total_volume = screen.query_one("#total-volume")
        assert market_status is not None
        assert active_agents is not None
        assert total_volume is not None


@pytest.mark.asyncio
async def test_trading_has_order_book_table() -> None:
    """Test that trading screen has order book table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TradingScreen)
        table = screen.query_one("#order-book-table")
        assert table is not None


@pytest.mark.asyncio
async def test_trading_has_trades_table() -> None:
    """Test that trading screen has trades table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TradingScreen)
        table = screen.query_one("#trades-table")
        assert table is not None


@pytest.mark.asyncio
async def test_trading_has_positions_table() -> None:
    """Test that trading screen has positions table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TradingScreen)
        table = screen.query_one("#positions-table")
        assert table is not None


@pytest.mark.asyncio
async def test_trading_has_log() -> None:
    """Test that trading screen has log widget."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TradingScreen)
        log = screen.query_one("#trading-log")
        assert log is not None


@pytest.mark.asyncio
async def test_agents_has_agent_table() -> None:
    """Test that agents screen has agent table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, AgentsScreen)
        table = screen.query_one("#agent-table")
        assert table is not None


@pytest.mark.asyncio
async def test_agents_has_buttons() -> None:
    """Test that agents screen has control buttons."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, AgentsScreen)
        pause_btn = screen.query_one("#pause-btn")
        resume_btn = screen.query_one("#resume-btn")
        assert pause_btn is not None
        assert resume_btn is not None


@pytest.mark.asyncio
async def test_leaderboard_has_table() -> None:
    """Test that leaderboard screen has table."""
    app = AVFApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, LeaderboardScreen)
        table = screen.query_one("#leaderboard-table")
        assert table is not None
