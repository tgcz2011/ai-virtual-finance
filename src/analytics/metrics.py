from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.portfolio.models import Trade


def calculate_returns(trades: list[Trade]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(trades)):
        prev_trade = trades[i - 1]
        curr_trade = trades[i]
        if prev_trade.price != 0:
            ret = (curr_trade.price - prev_trade.price) / prev_trade.price
            returns.append(ret)
    return returns


def calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.02) -> float:
    if len(returns) < 2:
        return 0.0
    avg_return = sum(returns) / len(returns)
    excess_return = avg_return - risk_free_rate / 252
    volatility = calculate_volatility(returns)
    if volatility == 0:
        return 0.0
    return (excess_return / volatility) * math.sqrt(252)


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    max_dd = 0.0
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak != 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def calculate_win_rate(trades: list[Trade]) -> float:
    if len(trades) < 2:
        return 0.0
    wins = 0
    total = 0
    for i in range(1, len(trades)):
        total += 1
        if trades[i].price >= trades[i - 1].price:
            wins += 1
    if total == 0:
        return 0.0
    return wins / total


def calculate_volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)


class PerformanceMetrics:
    @staticmethod
    def calculate_returns(trades: list[Trade]) -> list[float]:
        return calculate_returns(trades)

    @staticmethod
    def calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.02) -> float:
        return calculate_sharpe_ratio(returns, risk_free_rate)

    @staticmethod
    def calculate_max_drawdown(equity_curve: list[float]) -> float:
        return calculate_max_drawdown(equity_curve)

    @staticmethod
    def calculate_win_rate(trades: list[Trade]) -> float:
        return calculate_win_rate(trades)

    @staticmethod
    def calculate_volatility(returns: list[float]) -> float:
        return calculate_volatility(returns)
