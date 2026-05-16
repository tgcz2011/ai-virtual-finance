from __future__ import annotations

from datetime import datetime

import pytest

from src.data.calendar.trading_calendar import CryptoCalendar, USStockCalendar
from src.engine.market.state_machine import MarketState, MarketStateMachine


class TestMarketStateMachineUSStock:
    @pytest.fixture
    def us_machine(self) -> MarketStateMachine:
        return MarketStateMachine(USStockCalendar())

    def test_pre_market_state(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 7, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.PRE_MARKET

    def test_open_state(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 10, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.OPEN

    def test_post_market_state(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 18, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.POST_MARKET

    def test_closed_before_pre_market(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 3, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.CLOSED

    def test_closed_after_post_market(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 21, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.CLOSED

    def test_closed_on_holiday(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 10, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.CLOSED

    def test_closed_on_weekend(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 6, 10, 0, 0)
        assert us_machine.get_state("AAPL", ts) == MarketState.CLOSED

    def test_can_trade_during_open(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 10, 0, 0)
        assert us_machine.can_trade("AAPL", ts) is True

    def test_can_trade_during_pre_market(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 7, 0, 0)
        assert us_machine.can_trade("AAPL", ts) is True

    def test_can_trade_during_post_market(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 18, 0, 0)
        assert us_machine.can_trade("AAPL", ts) is True

    def test_cannot_trade_when_closed(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 21, 0, 0)
        assert us_machine.can_trade("AAPL", ts) is False

    def test_next_open_same_day(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 7, 0, 0)
        result = us_machine.next_open(ts)
        assert result == datetime(2024, 1, 2, 9, 30)

    def test_next_open_next_trading_day(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 21, 0, 0)
        result = us_machine.next_open(ts)
        assert result == datetime(2024, 1, 3, 9, 30)

    def test_next_open_skips_weekend(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 5, 21, 0, 0)
        result = us_machine.next_open(ts)
        assert result == datetime(2024, 1, 8, 9, 30)

    def test_next_close_during_open(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 10, 0, 0)
        result = us_machine.next_close(ts)
        assert result == datetime(2024, 1, 2, 16, 0)

    def test_next_close_during_post_market(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 18, 0, 0)
        result = us_machine.next_close(ts)
        assert result == datetime(2024, 1, 2, 20, 0)

    def test_next_close_after_hours(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 2, 21, 0, 0)
        result = us_machine.next_close(ts)
        assert result == datetime(2024, 1, 3, 16, 0)

    def test_next_close_on_weekend(self, us_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 6, 10, 0, 0)
        result = us_machine.next_close(ts)
        assert result == datetime(2024, 1, 8, 16, 0)


class TestMarketStateMachineCrypto:
    @pytest.fixture
    def crypto_machine(self) -> MarketStateMachine:
        return MarketStateMachine(CryptoCalendar())

    def test_crypto_always_open(self, crypto_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 3, 0, 0)
        assert crypto_machine.get_state("BTC-USD", ts) == MarketState.OPEN

    def test_crypto_can_trade_anytime(self, crypto_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 3, 0, 0)
        assert crypto_machine.can_trade("BTC-USD", ts) is True

    def test_crypto_next_open_is_now(self, crypto_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 3, 0, 0)
        assert crypto_machine.next_open(ts) == ts

    def test_crypto_next_close_far_future(self, crypto_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 3, 0, 0)
        result = crypto_machine.next_close(ts)
        assert result > ts

    def test_crypto_usdt_symbol(self, crypto_machine: MarketStateMachine) -> None:
        ts = datetime(2024, 1, 1, 3, 0, 0)
        assert crypto_machine.get_state("BTCUSDT", ts) == MarketState.OPEN
        assert crypto_machine.can_trade("BTCUSDT", ts) is True


class TestMarketStateMachineEdgeCases:
    def test_exact_market_open_boundary(self) -> None:
        machine = MarketStateMachine(USStockCalendar())
        ts = datetime(2024, 1, 2, 9, 30, 0)
        assert machine.get_state("AAPL", ts) == MarketState.OPEN

    def test_exact_market_close_boundary(self) -> None:
        machine = MarketStateMachine(USStockCalendar())
        ts = datetime(2024, 1, 2, 16, 0, 0)
        assert machine.get_state("AAPL", ts) == MarketState.POST_MARKET

    def test_exact_pre_market_start_boundary(self) -> None:
        machine = MarketStateMachine(USStockCalendar())
        ts = datetime(2024, 1, 2, 4, 0, 0)
        assert machine.get_state("AAPL", ts) == MarketState.PRE_MARKET

    def test_exact_post_market_end_boundary(self) -> None:
        machine = MarketStateMachine(USStockCalendar())
        ts = datetime(2024, 1, 2, 20, 0, 0)
        assert machine.get_state("AAPL", ts) == MarketState.CLOSED
