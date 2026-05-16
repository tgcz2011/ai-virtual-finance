from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from src.engine.portfolio.models import OrderSide, Trade


class FeeBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    commission: float
    slippage: float
    tax: float
    total: float


class FeeCalculator(ABC):
    @abstractmethod
    def calculate(self, trade: Trade) -> FeeBreakdown:
        raise NotImplementedError


class USStockFeeCalculator(FeeCalculator):
    COMMISSION_PER_SHARE: float = 0.005
    MIN_COMMISSION: float = 1.0
    SLIPPAGE_RATE: float = 0.0001
    TAX_RATE: float = 0.30

    def calculate(self, trade: Trade) -> FeeBreakdown:
        qty = trade.quantity
        price = trade.price
        notional = qty * price

        commission = max(qty * self.COMMISSION_PER_SHARE, self.MIN_COMMISSION)
        slippage = notional * self.SLIPPAGE_RATE
        tax = notional * self.TAX_RATE if trade.side == OrderSide.SELL else 0.0
        total = commission + slippage + tax

        return FeeBreakdown(
            commission=commission,
            slippage=slippage,
            tax=tax,
            total=total,
        )


class CryptoFeeCalculator(FeeCalculator):
    FEE_RATE: float = 0.001
    SLIPPAGE_RATE: float = 0.0005

    def calculate(self, trade: Trade) -> FeeBreakdown:
        notional = trade.quantity * trade.price

        commission = notional * self.FEE_RATE
        slippage = notional * self.SLIPPAGE_RATE
        tax = 0.0
        total = commission + slippage + tax

        return FeeBreakdown(
            commission=commission,
            slippage=slippage,
            tax=tax,
            total=total,
        )
