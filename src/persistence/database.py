from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from src.engine.order.models import Order, OrderStatus
from src.engine.portfolio.models import Portfolio, Position, Trade


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self._db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def initialize(self) -> None:
        conn = await self._get_connection()
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL NOT NULL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                cash REAL NOT NULL,
                total_value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                positions_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_id);
            CREATE INDEX IF NOT EXISTS idx_orders_agent ON orders(agent_id);
            CREATE INDEX IF NOT EXISTS idx_portfolios_agent ON portfolios(agent_id);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_agent ON checkpoints(agent_id);
            """
        )
        await conn.commit()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def save_trade(self, trade: Trade) -> None:
        conn = await self._get_connection()
        trade_id = str(uuid.uuid4())
        agent_id = getattr(trade, "agent_id", "")
        fee = getattr(trade, "fee", 0.0)
        timestamp = getattr(trade, "timestamp", datetime.now(UTC))
        await conn.execute(
            """
            INSERT INTO trades (id, agent_id, symbol, side, quantity, price, fee, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                agent_id,
                trade.symbol,
                trade.side.value,
                trade.quantity,
                trade.price,
                fee,
                timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
            ),
        )
        await conn.commit()

    async def save_order(self, order: Order) -> None:
        conn = await self._get_connection()
        await conn.execute(
            """
            INSERT INTO orders (id, agent_id, symbol, side, type, quantity, price, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.id,
                order.agent_id,
                order.symbol,
                order.side.value,
                order.type.value,
                order.quantity,
                order.price,
                order.status.value,
                order.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def save_portfolio(self, portfolio: Portfolio) -> None:
        conn = await self._get_connection()
        positions_data: dict[str, Any] = {}
        for symbol, pos in portfolio.positions.items():
            positions_data[symbol] = pos.model_dump()
        await conn.execute(
            """
            INSERT INTO portfolios (agent_id, cash, total_value, timestamp, positions_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                portfolio.agent_id,
                portfolio.cash,
                portfolio.total_value,
                datetime.now(UTC).isoformat(),
                json.dumps(positions_data),
            ),
        )
        await conn.commit()

    async def get_trade_history(self, agent_id: str, limit: int = 100) -> list[Trade]:
        conn = await self._get_connection()
        async with conn.execute(
            """
            SELECT id, agent_id, symbol, side, quantity, price, fee, timestamp
            FROM trades
            WHERE agent_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (agent_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()

        trades: list[Trade] = []
        for row in rows:
            trade = Trade(
                id=row["id"],
                agent_id=row["agent_id"],
                symbol=row["symbol"],
                side=row["side"],
                quantity=row["quantity"],
                price=row["price"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                fee=row["fee"],
            )
            trades.append(trade)
        return trades

    async def get_orders(self, agent_id: str, limit: int = 100) -> list[Order]:
        conn = await self._get_connection()
        async with conn.execute(
            """
            SELECT id, agent_id, symbol, side, type, quantity, price, status, timestamp
            FROM orders
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()

        orders: list[Order] = []
        for row in rows:
            from src.engine.order.models import OrderSide, OrderType

            order = Order(
                id=row["id"],
                agent_id=row["agent_id"],
                symbol=row["symbol"],
                side=OrderSide(row["side"]),
                type=OrderType(row["type"]),
                quantity=row["quantity"],
                price=row["price"],
                status=OrderStatus(row["status"]),
                created_at=datetime.fromisoformat(row["timestamp"]),
            )
            orders.append(order)
        return orders

    async def get_portfolios(self, agent_id: str, limit: int = 100) -> list[Portfolio]:
        conn = await self._get_connection()
        async with conn.execute(
            """
            SELECT agent_id, cash, total_value, timestamp, positions_json
            FROM portfolios
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()

        portfolios: list[Portfolio] = []
        for row in rows:
            positions_data = json.loads(row["positions_json"])
            positions: dict[str, Position] = {}
            for symbol, data in positions_data.items():
                positions[symbol] = Position(**data)
            portfolio = Portfolio(
                agent_id=row["agent_id"],
                cash=row["cash"],
                positions=positions,
                total_value=row["total_value"],
                total_pnl=0.0,
            )
            portfolios.append(portfolio)
        return portfolios

    async def save_checkpoint(self, checkpoint_id: str, agent_id: str, data_json: str, created_at: str) -> None:
        conn = await self._get_connection()
        await conn.execute(
            """
            INSERT INTO checkpoints (id, agent_id, data_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (checkpoint_id, agent_id, data_json, created_at),
        )
        await conn.commit()

    async def get_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT id, agent_id, data_json, created_at FROM checkpoints WHERE id = ?",
            (checkpoint_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "agent_id": row["agent_id"],
            "data_json": row["data_json"],
            "created_at": row["created_at"],
        }

    async def list_checkpoints(self, agent_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT id, agent_id, data_json, created_at FROM checkpoints WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "agent_id": row["agent_id"],
                "data_json": row["data_json"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        conn = await self._get_connection()
        cursor = await conn.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
        await conn.commit()
        return cursor.rowcount > 0
