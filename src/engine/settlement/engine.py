from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.engine.fee.calculator import FeeBreakdown
from src.engine.portfolio.models import Trade

if TYPE_CHECKING:
    from src.engine.fee.calculator import FeeCalculator
    from src.engine.portfolio.manager import PortfolioManager


class SettlementStatus(StrEnum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


class SettlementResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade: Trade
    fee_breakdown: FeeBreakdown
    settled_at: datetime
    status: SettlementStatus


class PendingSettlement(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade: Trade
    settlement_date: date
    status: SettlementStatus = Field(default=SettlementStatus.PENDING)


class SettlementEngine:
    def __init__(
        self,
        portfolio_manager: PortfolioManager,
        fee_calculator: FeeCalculator,
    ) -> None:
        self._portfolio_manager = portfolio_manager
        self._fee_calculator = fee_calculator
        self._pending_settlements: list[PendingSettlement] = []

    def _is_crypto(self, symbol: str) -> bool:
        return symbol.upper().endswith("-USD") or symbol.upper().endswith("USDT")

    def _calculate_settlement_date(self, trade_date: date) -> date:
        current = trade_date
        days_added = 0
        while days_added < 2:
            current += timedelta(days=1)
            if current.weekday() < 5:
                days_added += 1
        return current

    def settle(self, trade: Trade, trade_date: date | None = None) -> SettlementResult:
        fee_breakdown = self._fee_calculator.calculate(trade)

        if self._is_crypto(trade.symbol):
            self._portfolio_manager.update_position(trade)
            return SettlementResult(
                trade=trade,
                fee_breakdown=fee_breakdown,
                settled_at=datetime.now(UTC),
                status=SettlementStatus.SETTLED,
            )

        settlement_date = self._calculate_settlement_date(
            trade_date if trade_date is not None else date.today()
        )
        pending = PendingSettlement(
            trade=trade,
            settlement_date=settlement_date,
            status=SettlementStatus.PENDING,
        )
        self._pending_settlements.append(pending)

        return SettlementResult(
            trade=trade,
            fee_breakdown=fee_breakdown,
            settled_at=datetime.now(UTC),
            status=SettlementStatus.PENDING,
        )

    def daily_settlement(self, settlement_date: date) -> list[SettlementResult]:
        results: list[SettlementResult] = []
        remaining: list[PendingSettlement] = []

        for pending in self._pending_settlements:
            if pending.settlement_date <= settlement_date:
                self._portfolio_manager.update_position(pending.trade)
                fee_breakdown = self._fee_calculator.calculate(pending.trade)
                results.append(
                    SettlementResult(
                        trade=pending.trade,
                        fee_breakdown=fee_breakdown,
                        settled_at=datetime.now(UTC),
                        status=SettlementStatus.SETTLED,
                    )
                )
            else:
                remaining.append(pending)

        self._pending_settlements = remaining
        return results
