from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, time

from pydantic import BaseModel, Field

from src.engine.order.models import Order, OrderSide
from src.engine.portfolio.models import Portfolio


class ValidationResult(BaseModel):
    model_config = {"frozen": True}

    valid: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="List of validation error messages")


class OrderValidationRule(ABC):
    """Abstract base class for order validation rules."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Rule priority (lower = higher priority)."""

    @abstractmethod
    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        """Validate an order against a portfolio."""


class SufficientFundsRule(OrderValidationRule):
    """Check if portfolio has sufficient funds for the order."""

    @property
    def priority(self) -> int:
        return 1

    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        if order.side != OrderSide.BUY:
            return ValidationResult(valid=True)

        if order.price is None:
            return ValidationResult(valid=True)

        required_funds = order.quantity * order.price
        if portfolio.cash >= required_funds:
            return ValidationResult(valid=True)

        return ValidationResult(
            valid=False,
            errors=[
                f"Insufficient funds: required {required_funds:.2f}, "
                f"available {portfolio.cash:.2f}"
            ],
        )


class PositionLimitRule(OrderValidationRule):
    """Check if order would exceed position concentration limit."""

    def __init__(self, max_position_ratio: float = 0.30) -> None:
        self._max_position_ratio = max_position_ratio

    @property
    def priority(self) -> int:
        return 2

    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        if order.side != OrderSide.BUY or order.price is None:
            return ValidationResult(valid=True)

        current_position = portfolio.positions.get(order.symbol)
        current_value = current_position.market_value if current_position else 0.0
        new_value = current_value + order.quantity * order.price

        if portfolio.total_value <= 0:
            return ValidationResult(
                valid=False,
                errors=["Portfolio total value must be positive for position limit check"],
            )

        ratio = new_value / portfolio.total_value
        if ratio > self._max_position_ratio:
            return ValidationResult(
                valid=False,
                errors=[
                    f"Position limit exceeded for {order.symbol}: "
                    f"would be {ratio:.2%}, max allowed {self._max_position_ratio:.2%}"
                ],
            )

        return ValidationResult(valid=True)


class OrderSizeRule(OrderValidationRule):
    """Check if order size is within allowed limits."""

    def __init__(
        self,
        min_quantity: float = 1.0,
        max_quantity: float | None = None,
        max_notional: float | None = None,
    ) -> None:
        self._min_quantity = min_quantity
        self._max_quantity = max_quantity
        self._max_notional = max_notional

    @property
    def priority(self) -> int:
        return 3

    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        errors: list[str] = []

        if order.quantity < self._min_quantity:
            errors.append(
                f"Order quantity {order.quantity} below minimum {self._min_quantity}"
            )

        if self._max_quantity is not None and order.quantity > self._max_quantity:
            errors.append(
                f"Order quantity {order.quantity} above maximum {self._max_quantity}"
            )

        if self._max_notional is not None and order.price is not None:
            notional = order.quantity * order.price
            if notional > self._max_notional:
                errors.append(
                    f"Order notional {notional:.2f} above maximum {self._max_notional:.2f}"
                )

        if errors:
            return ValidationResult(valid=False, errors=errors)

        return ValidationResult(valid=True)


class PriceLimitRule(OrderValidationRule):
    """Check if order price is within daily price limit (e.g., A股 ±10%)."""

    def __init__(
        self,
        price_limit_ratio: float = 0.10,
        reference_prices: dict[str, float] | None = None,
    ) -> None:
        self._price_limit_ratio = price_limit_ratio
        self._reference_prices = reference_prices or {}

    @property
    def priority(self) -> int:
        return 4

    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        if order.price is None:
            return ValidationResult(valid=True)

        reference_price = self._reference_prices.get(order.symbol)
        if reference_price is None or reference_price <= 0:
            return ValidationResult(valid=True)

        lower_limit = reference_price * (1 - self._price_limit_ratio)
        upper_limit = reference_price * (1 + self._price_limit_ratio)

        if order.price < lower_limit:
            return ValidationResult(
                valid=False,
                errors=[
                    f"Price {order.price} below lower limit {lower_limit:.2f} "
                    f"(-{self._price_limit_ratio:.0%})"
                ],
            )

        if order.price > upper_limit:
            return ValidationResult(
                valid=False,
                errors=[
                    f"Price {order.price} above upper limit {upper_limit:.2f} "
                    f"(+{self._price_limit_ratio:.0%})"
                ],
            )

        return ValidationResult(valid=True)


class MarketHoursRule(OrderValidationRule):
    """Check if current time is within market trading hours."""

    def __init__(
        self,
        market_open: time = time(9, 30),
        market_close: time = time(15, 0),
        check_pre_market: bool = False,
    ) -> None:
        self._market_open = market_open
        self._market_close = market_close
        self._check_pre_market = check_pre_market

    @property
    def priority(self) -> int:
        return 5

    def validate(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        now = datetime.now().time()

        if self._market_open <= now <= self._market_close:
            return ValidationResult(valid=True)

        if self._check_pre_market:
            pre_market_end = time(9, 30)
            pre_market_start = time(9, 15)
            if pre_market_start <= now <= pre_market_end:
                return ValidationResult(valid=True)

        return ValidationResult(
            valid=False,
            errors=[
                f"Market is closed. Trading hours: "
                f"{self._market_open.strftime('%H:%M')}-"
                f"{self._market_close.strftime('%H:%M')}"
            ],
        )
