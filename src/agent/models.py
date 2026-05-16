from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.engine.order.models import Order, Trade
from src.engine.portfolio.models import Portfolio


class AgentStatus(Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    TRADING = "TRADING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    llm_provider: str = Field(..., description="LLM provider identifier")
    initial_capital: float = Field(..., gt=0, description="Initial capital")
    strategy_description: str = Field(..., description="Strategy description")
    risk_tolerance: float = Field(..., ge=0, le=1, description="Risk tolerance level")
    max_positions: int = Field(..., gt=0, description="Maximum number of positions")
    allowed_asset_types: list[str] = Field(default_factory=list, description="Allowed asset types")


class TradeAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: str = Field(..., description="BUY, SELL, or HOLD")
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(default=0, ge=0, description="Quantity to trade")
    reason: str = Field(default="", description="Reason for the action")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence level")

    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, v: object) -> str:
        if isinstance(v, str):
            v_upper = v.upper()
            if v_upper in {"BUY", "SELL", "HOLD"}:
                return v_upper
        raise ValueError("action must be BUY, SELL, or HOLD")


class AgentState(BaseModel):
    model_config = ConfigDict(frozen=False)

    config: AgentConfig = Field(..., description="Agent configuration")
    portfolio: Portfolio = Field(..., description="Current portfolio")
    active_orders: list[Order] = Field(default_factory=list, description="Active orders")
    trade_history: list[Trade] = Field(default_factory=list, description="Trade history")
    status: AgentStatus = Field(default=AgentStatus.IDLE, description="Current status")
