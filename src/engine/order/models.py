from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order(BaseModel):
    id: str = Field(..., description="Unique order identifier")
    agent_id: str = Field(..., description="Agent who placed the order")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Buy or sell")
    type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Total order quantity")
    price: float | None = Field(default=None, ge=0, description="Limit price")
    stop_price: float | None = Field(default=None, ge=0, description="Stop price")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Current status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    filled_quantity: float = Field(default=0.0, ge=0, description="Filled quantity")
    average_price: float = Field(default=0.0, ge=0, description="Average fill price")

    @field_validator("price", "stop_price", mode="before")
    @classmethod
    def validate_optional_price(cls, v: object) -> object:
        if v is not None and isinstance(v, (int, float)) and v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("filled_quantity", "average_price", mode="before")
    @classmethod
    def validate_non_negative(cls, v: object) -> object:
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("Value must be non-negative")
        return v

    model_config = {"frozen": False}

    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED or self.remaining_quantity() <= 0

    def is_active(self) -> bool:
        return self.status in {
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        }


class Trade(BaseModel):
    id: str = Field(..., description="Unique trade identifier")
    buy_order_id: str = Field(..., description="Buy order ID")
    sell_order_id: str = Field(..., description="Sell order ID")
    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(..., gt=0, description="Traded quantity")
    price: float = Field(..., gt=0, description="Trade price")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Trade timestamp")
    fee: float = Field(default=0.0, ge=0, description="Trading fee")

    model_config = {"frozen": True}
