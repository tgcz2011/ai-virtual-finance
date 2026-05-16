from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType
from src.engine.portfolio.models import OrderSide as PortfolioOrderSide
from src.engine.portfolio.models import Portfolio, Position, Trade
from src.persistence.database import DatabaseManager


@pytest_asyncio.fixture
async def db_manager():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = DatabaseManager(path)
    await manager.initialize()
    yield manager
    await manager.close()
    if os.path.exists(path):
        os.remove(path)


class TestDatabaseManager:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, db_manager: DatabaseManager) -> None:
        conn = await db_manager._get_connection()
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            rows = await cursor.fetchall()
        table_names = {row["name"] for row in rows}
        assert "trades" in table_names
        assert "orders" in table_names
        assert "portfolios" in table_names
        assert "checkpoints" in table_names

    @pytest.mark.asyncio
    async def test_save_and_get_trade(self, db_manager: DatabaseManager) -> None:
        trade = Trade(
            id="t1",
            agent_id="agent-1",
            symbol="AAPL",
            side=PortfolioOrderSide.BUY,
            quantity=10,
            price=150.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            fee=1.5,
        )
        await db_manager.save_trade(trade)
        trades = await db_manager.get_trade_history("agent-1")
        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"
        assert trades[0].quantity == 10
        assert trades[0].price == 150.0

    @pytest.mark.asyncio
    async def test_get_trade_history_limit(self, db_manager: DatabaseManager) -> None:
        for i in range(5):
            trade = Trade(
                id=f"t{i}",
                agent_id="agent-1",
                symbol="AAPL",
                side=PortfolioOrderSide.BUY,
                quantity=1,
                price=100.0 + i,
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                fee=0.0,
            )
            await db_manager.save_trade(trade)
        trades = await db_manager.get_trade_history("agent-1", limit=3)
        assert len(trades) == 3

    @pytest.mark.asyncio
    async def test_save_and_get_order(self, db_manager: DatabaseManager) -> None:
        order = Order(
            id="o1",
            agent_id="agent-1",
            symbol="TSLA",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=5.0,
            price=200.0,
            status=OrderStatus.FILLED,
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        await db_manager.save_order(order)
        orders = await db_manager.get_orders("agent-1")
        assert len(orders) == 1
        assert orders[0].id == "o1"
        assert orders[0].symbol == "TSLA"
        assert orders[0].status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_save_and_get_portfolio(self, db_manager: DatabaseManager) -> None:
        position = Position(
            symbol="AAPL",
            quantity=10,
            average_cost=150.0,
            current_price=155.0,
            unrealized_pnl=50.0,
            realized_pnl=0.0,
            market_value=1550.0,
        )
        portfolio = Portfolio(
            agent_id="agent-1",
            cash=8450.0,
            positions={"AAPL": position},
            total_value=10000.0,
            total_pnl=50.0,
        )
        await db_manager.save_portfolio(portfolio)
        portfolios = await db_manager.get_portfolios("agent-1")
        assert len(portfolios) == 1
        assert portfolios[0].agent_id == "agent-1"
        assert portfolios[0].cash == 8450.0
        assert portfolios[0].positions["AAPL"].quantity == 10

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, db_manager: DatabaseManager) -> None:
        await db_manager.save_checkpoint("cp1", "agent-1", '{"key": "value"}', "2024-01-01T12:00:00")
        cp = await db_manager.get_checkpoint("cp1")
        assert cp is not None
        assert cp["agent_id"] == "agent-1"
        assert cp["data_json"] == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, db_manager: DatabaseManager) -> None:
        await db_manager.save_checkpoint("cp1", "agent-1", "{}", "2024-01-01T12:00:00")
        await db_manager.save_checkpoint("cp2", "agent-1", "{}", "2024-01-02T12:00:00")
        cps = await db_manager.list_checkpoints("agent-1")
        assert len(cps) == 2

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, db_manager: DatabaseManager) -> None:
        await db_manager.save_checkpoint("cp1", "agent-1", "{}", "2024-01-01T12:00:00")
        result = await db_manager.delete_checkpoint("cp1")
        assert result is True
        cp = await db_manager.get_checkpoint("cp1")
        assert cp is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_checkpoint(self, db_manager: DatabaseManager) -> None:
        result = await db_manager.delete_checkpoint("cp-missing")
        assert result is False
