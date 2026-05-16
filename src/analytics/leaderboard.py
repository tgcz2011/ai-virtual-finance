from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.analytics.metrics import (
    calculate_max_drawdown,
    calculate_returns,
    calculate_sharpe_ratio,
    calculate_win_rate,
)
from src.engine.portfolio.models import Trade
from src.persistence.database import DatabaseManager


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(default="", description="Agent display name")
    total_return: float = Field(default=0.0, description="Total return ratio")
    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")
    max_drawdown: float = Field(default=0.0, description="Maximum drawdown ratio")
    win_rate: float = Field(default=0.0, description="Win rate ratio")
    total_trades: int = Field(default=0, description="Total number of trades")
    rank: int = Field(default=0, description="Leaderboard rank")


class Leaderboard:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    async def calculate_rankings(self) -> list[LeaderboardEntry]:
        conn = await self._db._get_connection()
        async with conn.execute(
            "SELECT DISTINCT agent_id FROM trades"
        ) as cursor:
            rows = await cursor.fetchall()

        agent_ids = [row["agent_id"] for row in rows if row["agent_id"]]
        entries: list[LeaderboardEntry] = []
        for agent_id in agent_ids:
            entry = await self.get_agent_stats(agent_id)
            if entry is not None:
                entries.append(entry)

        entries.sort(key=lambda e: e.total_return, reverse=True)
        ranked: list[LeaderboardEntry] = []
        for i, entry in enumerate(entries, start=1):
            ranked.append(entry.model_copy(update={"rank": i}))
        return ranked

    async def get_agent_stats(self, agent_id: str) -> LeaderboardEntry | None:
        trades = await self._db.get_trade_history(agent_id, limit=10000)
        if not trades:
            return None

        total_trades = len(trades)
        returns = calculate_returns(trades)

        equity_curve = self._build_equity_curve(trades)
        total_return = self._calculate_total_return(equity_curve)
        sharpe = calculate_sharpe_ratio(returns) if returns else 0.0
        max_dd = calculate_max_drawdown(equity_curve) if equity_curve else 0.0
        win_rate = calculate_win_rate(trades)

        return LeaderboardEntry(
            agent_id=agent_id,
            agent_name=agent_id,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            total_trades=total_trades,
            rank=0,
        )

    async def get_top_performers(self, limit: int = 10) -> list[LeaderboardEntry]:
        rankings = await self.calculate_rankings()
        return rankings[:limit]

    @staticmethod
    def _build_equity_curve(trades: list[Trade]) -> list[float]:
        if not trades:
            return []
        equity: list[float] = [10000.0]
        for trade in trades:
            current = equity[-1]
            if trade.side.value == "buy":
                equity.append(current - trade.quantity * trade.price)
            else:
                equity.append(current + trade.quantity * trade.price)
        return equity

    @staticmethod
    def _calculate_total_return(equity_curve: list[float]) -> float:
        if len(equity_curve) < 2:
            return 0.0
        initial = equity_curve[0]
        final = equity_curve[-1]
        if initial == 0:
            return 0.0
        return (final - initial) / initial
