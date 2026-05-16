from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from src.engine.portfolio.models import Portfolio


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskResult(BaseModel):
    model_config = {"frozen": True}

    level: RiskLevel = Field(..., description="Risk assessment level")
    messages: list[str] = Field(default_factory=list, description="List of risk messages")


class RiskRule(ABC):
    """Abstract base class for risk evaluation rules."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Rule priority (lower = higher priority)."""

    @abstractmethod
    def evaluate(self, portfolio: Portfolio, market_data: dict[str, float]) -> RiskResult:
        """Evaluate portfolio risk given current market data."""


class ConcentrationRiskRule(RiskRule):
    """Check portfolio concentration risk (single position too large)."""

    def __init__(
        self,
        warning_threshold: float = 0.25,
        critical_threshold: float = 0.40,
    ) -> None:
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold

    @property
    def priority(self) -> int:
        return 1

    def evaluate(self, portfolio: Portfolio, market_data: dict[str, float]) -> RiskResult:
        if portfolio.total_value <= 0:
            return RiskResult(
                level=RiskLevel.CRITICAL,
                messages=["Portfolio total value is zero or negative"],
            )

        messages: list[str] = []
        max_ratio = 0.0
        max_symbol = ""

        for symbol, position in portfolio.positions.items():
            ratio = position.market_value / portfolio.total_value
            if ratio > max_ratio:
                max_ratio = ratio
                max_symbol = symbol

        if max_ratio >= self._critical_threshold:
            messages.append(
                f"Critical concentration: {max_symbol} is {max_ratio:.2%} of portfolio, "
                f"exceeds critical threshold {self._critical_threshold:.2%}"
            )
            return RiskResult(level=RiskLevel.CRITICAL, messages=messages)

        if max_ratio >= self._warning_threshold:
            messages.append(
                f"High concentration: {max_symbol} is {max_ratio:.2%} of portfolio, "
                f"exceeds warning threshold {self._warning_threshold:.2%}"
            )
            return RiskResult(level=RiskLevel.HIGH, messages=messages)

        if max_ratio > 0:
            messages.append(
                f"Concentration OK: largest position {max_symbol} is {max_ratio:.2%}"
            )
            return RiskResult(level=RiskLevel.LOW, messages=messages)

        return RiskResult(level=RiskLevel.LOW, messages=["No positions held"])


class DrawdownRiskRule(RiskRule):
    """Check portfolio drawdown risk from peak value."""

    def __init__(
        self,
        warning_threshold: float = 0.10,
        critical_threshold: float = 0.20,
    ) -> None:
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._peak_value: float = 0.0

    @property
    def priority(self) -> int:
        return 2

    def evaluate(self, portfolio: Portfolio, market_data: dict[str, float]) -> RiskResult:
        self._peak_value = max(self._peak_value, portfolio.total_value)

        if self._peak_value <= 0:
            return RiskResult(level=RiskLevel.LOW, messages=["No peak value recorded yet"])

        drawdown = (self._peak_value - portfolio.total_value) / self._peak_value

        if drawdown >= self._critical_threshold:
            return RiskResult(
                level=RiskLevel.CRITICAL,
                messages=[
                    f"Critical drawdown: {drawdown:.2%} from peak {self._peak_value:.2f}, "
                    f"exceeds critical threshold {self._critical_threshold:.2%}"
                ],
            )

        if drawdown >= self._warning_threshold:
            return RiskResult(
                level=RiskLevel.HIGH,
                messages=[
                    f"High drawdown: {drawdown:.2%} from peak {self._peak_value:.2f}, "
                    f"exceeds warning threshold {self._warning_threshold:.2%}"
                ],
            )

        if drawdown > 0:
            return RiskResult(
                level=RiskLevel.MEDIUM,
                messages=[
                    f"Moderate drawdown: {drawdown:.2%} from peak {self._peak_value:.2f}"
                ],
            )

        return RiskResult(
            level=RiskLevel.LOW,
            messages=[f"No drawdown: portfolio at peak {self._peak_value:.2f}"],
        )


class LeverageRiskRule(RiskRule):
    """Check portfolio leverage risk (borrowed funds vs equity)."""

    def __init__(
        self,
        warning_threshold: float = 1.5,
        critical_threshold: float = 2.0,
    ) -> None:
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold

    @property
    def priority(self) -> int:
        return 3

    def evaluate(self, portfolio: Portfolio, market_data: dict[str, float]) -> RiskResult:
        equity = max(portfolio.cash, 0.0)
        total_assets = portfolio.total_value

        if equity <= 0 and total_assets > 0:
            return RiskResult(
                level=RiskLevel.CRITICAL,
                messages=[
                    "Critical leverage: no equity but holding positions, "
                    "effectively infinite leverage"
                ],
            )

        if equity <= 0:
            return RiskResult(
                level=RiskLevel.LOW,
                messages=["No equity or positions"],
            )

        leverage = total_assets / equity

        if leverage >= self._critical_threshold:
            return RiskResult(
                level=RiskLevel.CRITICAL,
                messages=[
                    f"Critical leverage: {leverage:.2f}x, "
                    f"exceeds critical threshold {self._critical_threshold:.2f}x"
                ],
            )

        if leverage >= self._warning_threshold:
            return RiskResult(
                level=RiskLevel.HIGH,
                messages=[
                    f"High leverage: {leverage:.2f}x, "
                    f"exceeds warning threshold {self._warning_threshold:.2f}x"
                ],
            )

        if leverage > 1.0:
            return RiskResult(
                level=RiskLevel.MEDIUM,
                messages=[f"Moderate leverage: {leverage:.2f}x"],
            )

        return RiskResult(
            level=RiskLevel.LOW,
            messages=[f"Low leverage: {leverage:.2f}x"],
        )
