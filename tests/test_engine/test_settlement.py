from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.engine.fee.calculator import CryptoFeeCalculator, USStockFeeCalculator
from src.engine.portfolio.manager import PortfolioManager
from src.engine.portfolio.models import OrderSide, Trade
from src.engine.settlement.engine import (
    PendingSettlement,
    SettlementEngine,
    SettlementResult,
    SettlementStatus,
)


class TestSettlementEngine:
    @pytest.fixture
    def portfolio_manager(self) -> PortfolioManager:
        return PortfolioManager(agent_id="test-agent", initial_cash=100000.0)

    @pytest.fixture
    def stock_engine(self, portfolio_manager: PortfolioManager) -> SettlementEngine:
        return SettlementEngine(
            portfolio_manager=portfolio_manager,
            fee_calculator=USStockFeeCalculator(),
        )

    @pytest.fixture
    def crypto_engine(self, portfolio_manager: PortfolioManager) -> SettlementEngine:
        return SettlementEngine(
            portfolio_manager=portfolio_manager,
            fee_calculator=CryptoFeeCalculator(),
        )

    def test_stock_t2_settlement_pending(self, stock_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        result = stock_engine.settle(trade, trade_date=date(2024, 1, 2))

        assert isinstance(result, SettlementResult)
        assert result.status == SettlementStatus.PENDING
        assert result.trade.symbol == "AAPL"
        assert result.fee_breakdown.total > 0

    def test_stock_t2_settlement_date_calculation(self, stock_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        stock_engine.settle(trade, trade_date=date(2024, 1, 2))

        pending = stock_engine._pending_settlements
        assert len(pending) == 1
        assert pending[0].settlement_date == date(2024, 1, 4)

    def test_crypto_immediate_settlement(self, crypto_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="BTC-USD",
            quantity=1,
            price=50000.0,
            side=OrderSide.BUY,
        )
        result = crypto_engine.settle(trade)

        assert result.status == SettlementStatus.SETTLED
        assert len(crypto_engine._pending_settlements) == 0

    def test_crypto_usdt_symbol(self, crypto_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="BTCUSDT",
            quantity=1,
            price=50000.0,
            side=OrderSide.BUY,
        )
        result = crypto_engine.settle(trade)

        assert result.status == SettlementStatus.SETTLED
        assert len(crypto_engine._pending_settlements) == 0

    def test_daily_settlement_processes_due_trades(self, stock_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        stock_engine.settle(trade, trade_date=date(2024, 1, 2))
        assert len(stock_engine._pending_settlements) == 1

        results = stock_engine.daily_settlement(date(2024, 1, 4))

        assert len(results) == 1
        assert results[0].status == SettlementStatus.SETTLED
        assert len(stock_engine._pending_settlements) == 0

    def test_daily_settlement_skips_future_trades(self, stock_engine: SettlementEngine) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        stock_engine.settle(trade, trade_date=date(2024, 1, 2))

        results = stock_engine.daily_settlement(date(2024, 1, 3))

        assert len(results) == 0
        assert len(stock_engine._pending_settlements) == 1

    def test_daily_settlement_multiple_trades(self, stock_engine: SettlementEngine) -> None:
        trade1 = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        trade2 = Trade(
            symbol="GOOGL",
            quantity=5,
            price=100.0,
            side=OrderSide.BUY,
        )
        stock_engine.settle(trade1, trade_date=date(2024, 1, 2))
        stock_engine.settle(trade2, trade_date=date(2024, 1, 3))
        assert len(stock_engine._pending_settlements) == 2

        results = stock_engine.daily_settlement(date(2024, 1, 5))

        assert len(results) == 2
        assert all(r.status == SettlementStatus.SETTLED for r in results)
        assert len(stock_engine._pending_settlements) == 0

    def test_pending_settlement_model(self) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        pending = PendingSettlement(
            trade=trade,
            settlement_date=date(2024, 1, 4),
        )

        assert pending.trade.symbol == "AAPL"
        assert pending.settlement_date == date(2024, 1, 4)
        assert pending.status == SettlementStatus.PENDING

    def test_settlement_result_model(self) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        fee = USStockFeeCalculator().calculate(trade)
        result = SettlementResult(
            trade=trade,
            fee_breakdown=fee,
            settled_at=datetime.now(timezone.utc),
            status=SettlementStatus.SETTLED,
        )

        assert result.trade == trade
        assert result.status == SettlementStatus.SETTLED

    def test_stock_settlement_updates_portfolio_on_daily(self, stock_engine: SettlementEngine, portfolio_manager: PortfolioManager) -> None:
        trade = Trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            side=OrderSide.BUY,
        )
        stock_engine.settle(trade, trade_date=date(2024, 1, 2))

        portfolio_before = portfolio_manager.get_portfolio()
        assert portfolio_before.cash == 100000.0
        assert "AAPL" not in portfolio_before.positions

        stock_engine.daily_settlement(date(2024, 1, 4))

        portfolio_after = portfolio_manager.get_portfolio()
        assert portfolio_after.cash < 100000.0
        assert "AAPL" in portfolio_after.positions
        assert portfolio_after.positions["AAPL"].quantity == 10

    def test_crypto_settlement_updates_portfolio_immediately(self, crypto_engine: SettlementEngine, portfolio_manager: PortfolioManager) -> None:
        trade = Trade(
            symbol="BTC-USD",
            quantity=1,
            price=50000.0,
            side=OrderSide.BUY,
        )
        crypto_engine.settle(trade)

        portfolio = portfolio_manager.get_portfolio()
        assert portfolio.cash == 50000.0
        assert "BTC-USD" in portfolio.positions
        assert portfolio.positions["BTC-USD"].quantity == 1
