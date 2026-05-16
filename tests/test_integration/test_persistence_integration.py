from __future__ import annotations

import json
import os
import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio

from src.analytics.leaderboard import Leaderboard
from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType
from src.engine.portfolio.models import OrderSide as PortfolioOrderSide
from src.engine.portfolio.models import Portfolio, Position, Trade as PortfolioTrade
from src.persistence.checkpoint import AgentState, CheckpointManager
from src.persistence.database import DatabaseManager


@pytest_asyncio.fixture
async def db_manager() -> AsyncGenerator[DatabaseManager, Any]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    await db.initialize()
    yield db
    await db.close()
    if os.path.exists(path):
        os.remove(path)


@pytest_asyncio.fixture
async def checkpoint_manager(db_manager: DatabaseManager) -> AsyncGenerator[CheckpointManager, Any]:
    yield CheckpointManager(db_manager)


@pytest_asyncio.fixture
async def leaderboard(db_manager: DatabaseManager) -> AsyncGenerator[Leaderboard, Any]:
    yield Leaderboard(db_manager)


class TestTradePersistence:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_trade(self, db_manager: DatabaseManager) -> None:
        trade = PortfolioTrade(
            id="trade-001",
            agent_id="agent-1",
            symbol="AAPL",
            side=PortfolioOrderSide.BUY,
            quantity=100,
            price=150.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            fee=1.5,
        )
        await db_manager.save_trade(trade)

        trades = await db_manager.get_trade_history("agent-1")
        assert len(trades) == 1
        retrieved = trades[0]
        assert retrieved.agent_id == "agent-1"
        assert retrieved.symbol == "AAPL"
        assert retrieved.quantity == 100
        assert retrieved.price == 150.0
        assert retrieved.fee == 1.5

    @pytest.mark.asyncio
    async def test_multiple_trades_persisted(self, db_manager: DatabaseManager) -> None:
        for i in range(5):
            trade = PortfolioTrade(
                id=f"trade-{i}",
                agent_id="agent-multi",
                symbol="TSLA",
                side=PortfolioOrderSide.BUY if i % 2 == 0 else PortfolioOrderSide.SELL,
                quantity=10 + i,
                price=200.0 + i,
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                fee=0.0,
            )
            await db_manager.save_trade(trade)

        trades = await db_manager.get_trade_history("agent-multi")
        assert len(trades) == 5
        sides = {t.side.value for t in trades}
        assert sides == {"buy", "sell"}


class TestOrderPersistence:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_order(self, db_manager: DatabaseManager) -> None:
        order = Order(
            id="order-001",
            agent_id="agent-1",
            symbol="MSFT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=50,
            price=300.0,
            status=OrderStatus.OPEN,
            created_at=datetime(2024, 6, 1, 9, 30, 0, tzinfo=UTC),
        )
        await db_manager.save_order(order)

        orders = await db_manager.get_orders("agent-1")
        assert len(orders) == 1
        retrieved = orders[0]
        assert retrieved.id == "order-001"
        assert retrieved.symbol == "MSFT"
        assert retrieved.side == OrderSide.BUY
        assert retrieved.type == OrderType.LIMIT
        assert retrieved.quantity == 50
        assert retrieved.price == 300.0
        assert retrieved.status == OrderStatus.OPEN


class TestPortfolioPersistence:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_portfolio(self, db_manager: DatabaseManager) -> None:
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=150.0,
            current_price=155.0,
            unrealized_pnl=500.0,
            realized_pnl=0.0,
            market_value=15500.0,
        )
        portfolio = Portfolio(
            agent_id="agent-1",
            cash=50000.0,
            positions={"AAPL": position},
            total_value=65500.0,
            total_pnl=500.0,
        )
        await db_manager.save_portfolio(portfolio)

        portfolios = await db_manager.get_portfolios("agent-1")
        assert len(portfolios) == 1
        retrieved = portfolios[0]
        assert retrieved.agent_id == "agent-1"
        assert retrieved.cash == 50000.0
        assert retrieved.total_value == 65500.0
        assert "AAPL" in retrieved.positions
        assert retrieved.positions["AAPL"].quantity == 100


class TestCheckpointPersistence:
    @pytest.mark.asyncio
    async def test_create_and_restore_checkpoint(
        self, checkpoint_manager: CheckpointManager
    ) -> None:
        agent_id = "agent-checkpoint"
        state = AgentState(
            agent_id=agent_id,
            data={"cash": 10000.0, "positions": {"AAPL": 50}},
        )
        checkpoint_id = await checkpoint_manager.create_checkpoint(agent_id, state)
        assert checkpoint_id

        restored = await checkpoint_manager.restore_checkpoint(checkpoint_id)
        assert restored.agent_id == agent_id
        assert restored.data["cash"] == 10000.0
        assert restored.data["positions"]["AAPL"] == 50

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, checkpoint_manager: CheckpointManager) -> None:
        agent_id = "agent-list"
        for i in range(3):
            state = AgentState(agent_id=agent_id, data={"version": i})
            await checkpoint_manager.create_checkpoint(agent_id, state)

        checkpoints = await checkpoint_manager.list_checkpoints(agent_id)
        assert len(checkpoints) == 3

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        agent_id = "agent-delete"
        state = AgentState(agent_id=agent_id, data={"temp": True})
        checkpoint_id = await checkpoint_manager.create_checkpoint(agent_id, state)

        deleted = await checkpoint_manager.delete_checkpoint(checkpoint_id)
        assert deleted is True

        with pytest.raises(ValueError):
            await checkpoint_manager.restore_checkpoint(checkpoint_id)


class TestLeaderboardCalculations:
    @pytest.mark.asyncio
    async def test_leaderboard_rankings(self, leaderboard: Leaderboard) -> None:
        agent_a_trades = [
            PortfolioTrade(
                id="t1",
                agent_id="agent-a",
                symbol="AAPL",
                side=PortfolioOrderSide.BUY,
                quantity=10,
                price=100.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            PortfolioTrade(
                id="t2",
                agent_id="agent-a",
                symbol="AAPL",
                side=PortfolioOrderSide.SELL,
                quantity=10,
                price=120.0,
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                fee=0.0,
            ),
        ]
        agent_b_trades = [
            PortfolioTrade(
                id="t3",
                agent_id="agent-b",
                symbol="TSLA",
                side=PortfolioOrderSide.BUY,
                quantity=5,
                price=200.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                fee=0.0,
            ),
            PortfolioTrade(
                id="t4",
                agent_id="agent-b",
                symbol="TSLA",
                side=PortfolioOrderSide.SELL,
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
    async def test_leaderboard_stats_with_no_trades(self, leaderboard: Leaderboard) -> None:
        stats = await leaderboard.get_agent_stats("no-trades-agent")
        assert stats is None

    @pytest.mark.asyncio
    async def test_top_performers(self, leaderboard: Leaderboard) -> None:
        for i in range(15):
            trade = PortfolioTrade(
                id=f"t{i}",
                agent_id=f"agent-{i}",
                symbol="AAPL",
                side=PortfolioOrderSide.BUY,
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
