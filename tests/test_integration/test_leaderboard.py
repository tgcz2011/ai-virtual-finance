from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.analytics.leaderboard import Leaderboard, LeaderboardEntry
from src.engine.portfolio.models import OrderSide, Trade
from src.persistence.database import DatabaseManager


@pytest_asyncio.fixture
async def leaderboard():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    await db.initialize()
    lb = Leaderboard(db)
    yield lb
    await db.close()
    if os.path.exists(path):
        os.remove(path)


class TestLeaderboard:
    @pytest.mark.asyncio
    async def test_get_agent_stats_no_trades(self, leaderboard: Leaderboard) -> None:
        stats = await leaderboard.get_agent_stats("agent-no-trades")
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_agent_stats_with_trades(self, leaderboard: Leaderboard) -> None:
        trades = [
            Trade(
                id="t1",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=10,
                price=100.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            Trade(
                id="t2",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=10,
                price=110.0,
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                fee=0.0,
            ),
        ]
        for trade in trades:
            await leaderboard._db.save_trade(trade)

        stats = await leaderboard.get_agent_stats("agent-a")
        assert stats is not None
        assert stats.agent_id == "agent-a"
        assert stats.total_trades == 2
        assert stats.win_rate == 1.0

    @pytest.mark.asyncio
    async def test_calculate_rankings(self, leaderboard: Leaderboard) -> None:
        agent_a_trades = [
            Trade(
                id="t1",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=10,
                price=100.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            Trade(
                id="t2",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=10,
                price=120.0,
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                fee=0.0,
            ),
        ]
        agent_b_trades = [
            Trade(
                id="t3",
                agent_id="agent-b",
                symbol="TSLA",
                side=OrderSide.BUY,
                quantity=5,
                price=200.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            Trade(
                id="t4",
                agent_id="agent-b",
                symbol="TSLA",
                side=OrderSide.SELL,
                quantity=5,
                price=190.0,
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                fee=0.0,
            ),
        ]
        for trade in agent_a_trades + agent_b_trades:
            await leaderboard._db.save_trade(trade)

        rankings = await leaderboard.calculate_rankings()
        assert len(rankings) == 2
        assert rankings[0].agent_id == "agent-a"
        assert rankings[0].rank == 1
        assert rankings[1].agent_id == "agent-b"
        assert rankings[1].rank == 2

    @pytest.mark.asyncio
    async def test_get_top_performers(self, leaderboard: Leaderboard) -> None:
        for i in range(15):
            trade = Trade(
                id=f"t{i}",
                agent_id=f"agent-{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=1,
                price=100.0 + i,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            )
            await leaderboard._db.save_trade(trade)

        top = await leaderboard.get_top_performers(limit=5)
        assert len(top) == 5
        for entry in top:
            assert entry.rank > 0

    @pytest.mark.asyncio
    async def test_leaderboard_entry_model(self) -> None:
        entry = LeaderboardEntry(
            agent_id="agent-1",
            agent_name="Test Agent",
            total_return=0.15,
            sharpe_ratio=1.2,
            max_drawdown=0.05,
            win_rate=0.6,
            total_trades=100,
            rank=1,
        )
        assert entry.agent_id == "agent-1"
        assert entry.total_return == 0.15
        assert entry.rank == 1

    @pytest.mark.asyncio
    async def test_build_equity_curve(self, leaderboard: Leaderboard) -> None:
        trades = [
            Trade(
                id="t1",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=10,
                price=100.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            Trade(
                id="t2",
                agent_id="agent-a",
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=10,
                price=110.0,
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                fee=0.0,
            ),
        ]
        curve = Leaderboard._build_equity_curve(trades)
        assert curve[0] == 10000.0
        assert curve[-1] == 10100.0

    @pytest.mark.asyncio
    async def test_calculate_total_return(self, leaderboard: Leaderboard) -> None:
        ret = Leaderboard._calculate_total_return([10000.0, 11000.0])
        assert ret == 0.1
        assert Leaderboard._calculate_total_return([]) == 0.0
        assert Leaderboard._calculate_total_return([10000.0]) == 0.0
