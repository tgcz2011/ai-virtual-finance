from __future__ import annotations

from datetime import datetime, time, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from src.data.calendar.trading_calendar import CryptoCalendar, TradingCalendar, USStockCalendar

if TYPE_CHECKING:
    pass


class MarketState(StrEnum):
    CLOSED = "CLOSED"
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    POST_MARKET = "POST_MARKET"
    HALTED = "HALTED"


class MarketStateMachine:
    def __init__(self, calendar: TradingCalendar) -> None:
        self._calendar = calendar
        self._is_crypto = isinstance(calendar, CryptoCalendar)

    def _is_us_stock(self) -> bool:
        return isinstance(self._calendar, USStockCalendar)

    def get_state(self, symbol: str, timestamp: datetime) -> MarketState:
        if self._is_crypto or symbol.upper().endswith("-USD") or symbol.upper().endswith("USDT"):
            return MarketState.OPEN

        if not self._calendar.is_trading_day(timestamp.date()):
            return MarketState.CLOSED

        t = timestamp.time()
        pre_market_start = time(4, 0)
        market_open = time(9, 30)
        market_close = time(16, 0)
        post_market_end = time(20, 0)

        if t < pre_market_start or t >= post_market_end:
            return MarketState.CLOSED
        if pre_market_start <= t < market_open:
            return MarketState.PRE_MARKET
        if market_open <= t < market_close:
            return MarketState.OPEN
        if market_close <= t < post_market_end:
            return MarketState.POST_MARKET

        return MarketState.CLOSED

    def can_trade(self, symbol: str, timestamp: datetime) -> bool:
        if self._is_crypto or symbol.upper().endswith("-USD") or symbol.upper().endswith("USDT"):
            return True

        state = self.get_state(symbol, timestamp)
        return state in {MarketState.PRE_MARKET, MarketState.OPEN, MarketState.POST_MARKET}

    def next_open(self, timestamp: datetime) -> datetime:
        if self._is_crypto:
            return timestamp

        current_date = timestamp.date()
        t = timestamp.time()
        market_open = time(9, 30)

        if self._calendar.is_trading_day(current_date) and t < market_open:
            return datetime.combine(current_date, market_open)

        next_day = self._calendar.next_trading_day(current_date)
        return datetime.combine(next_day, market_open)

    def next_close(self, timestamp: datetime) -> datetime:
        if self._is_crypto:
            return timestamp + timedelta(days=365)

        current_date = timestamp.date()
        t = timestamp.time()
        market_close = time(16, 0)
        post_market_end = time(20, 0)

        if not self._calendar.is_trading_day(current_date):
            next_day = self._calendar.next_trading_day(current_date)
            return datetime.combine(next_day, market_close)

        if t < market_close:
            return datetime.combine(current_date, market_close)
        if t < post_market_end:
            return datetime.combine(current_date, post_market_end)

        next_day = self._calendar.next_trading_day(current_date)
        return datetime.combine(next_day, market_close)
