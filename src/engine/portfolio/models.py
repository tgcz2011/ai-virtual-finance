from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Trade(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    side: OrderSide


class Position(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    quantity: int
    average_cost: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    market_value: float


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    cash: float
    positions: dict[str, Position]
    total_value: float
    total_pnl: float
