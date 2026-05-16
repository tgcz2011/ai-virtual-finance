from __future__ import annotations

import pytest

from src.engine.portfolio.manager import PortfolioManager
from src.engine.portfolio.models import OrderSide, Trade


@pytest.fixture
def manager() -> PortfolioManager:
    return PortfolioManager(agent_id="test-agent", initial_cash=10000.0)


class TestPortfolioManager:
    def test_buy_new_position(self, manager: PortfolioManager) -> None:
        trade = Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY)
        manager.update_position(trade)

        pos = manager.get_position("AAPL")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.average_cost == 150.0
        assert pos.current_price == 150.0
        assert pos.unrealized_pnl == 0.0
        assert pos.realized_pnl == 0.0
        assert pos.market_value == 1500.0

        portfolio = manager.get_portfolio()
        assert portfolio.cash == 8500.0
        assert portfolio.total_value == 10000.0
        assert portfolio.total_pnl == 0.0

    def test_buy_existing_position(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY))
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=160.0, side=OrderSide.BUY))

        pos = manager.get_position("AAPL")
        assert pos is not None
        assert pos.quantity == 20
        assert pos.average_cost == 155.0
        assert pos.current_price == 160.0
        assert pos.unrealized_pnl == 100.0
        assert pos.realized_pnl == 0.0
        assert pos.market_value == 3200.0

        portfolio = manager.get_portfolio()
        assert portfolio.cash == 6900.0
        assert portfolio.total_value == 10100.0

    def test_sell_partial(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=20, price=150.0, side=OrderSide.BUY))
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=160.0, side=OrderSide.SELL))

        pos = manager.get_position("AAPL")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.average_cost == 150.0
        assert pos.current_price == 160.0
        assert pos.unrealized_pnl == 100.0
        assert pos.realized_pnl == 100.0
        assert pos.market_value == 1600.0

        portfolio = manager.get_portfolio()
        assert portfolio.cash == 8600.0
        assert portfolio.total_value == 10200.0
        assert portfolio.total_pnl == 200.0

    def test_sell_full(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY))
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=160.0, side=OrderSide.SELL))

        assert manager.get_position("AAPL") is None

        portfolio = manager.get_portfolio()
        assert portfolio.cash == 10100.0
        assert portfolio.total_value == 10100.0
        assert portfolio.total_pnl == 100.0

    def test_sell_insufficient(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=5, price=150.0, side=OrderSide.BUY))
        with pytest.raises(ValueError, match="Insufficient position"):
            manager.update_position(Trade(symbol="AAPL", quantity=10, price=160.0, side=OrderSide.SELL))

    def test_mark_to_market(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY))
        portfolio = manager.mark_to_market({"AAPL": 170.0})

        pos = portfolio.positions["AAPL"]
        assert pos.current_price == 170.0
        assert pos.unrealized_pnl == 200.0
        assert pos.market_value == 1700.0
        assert portfolio.total_value == 10200.0
        assert portfolio.total_pnl == 200.0

    def test_can_trade_buy(self, manager: PortfolioManager) -> None:
        assert manager.can_trade("AAPL", quantity=10, price=150.0, side=OrderSide.BUY) is True
        assert manager.can_trade("AAPL", quantity=100, price=150.0, side=OrderSide.BUY) is False

    def test_can_trade_sell(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY))
        assert manager.can_trade("AAPL", quantity=5, price=160.0, side=OrderSide.SELL) is True
        assert manager.can_trade("AAPL", quantity=15, price=160.0, side=OrderSide.SELL) is False
        assert manager.can_trade("TSLA", quantity=1, price=100.0, side=OrderSide.SELL) is False

    def test_can_trade_invalid(self, manager: PortfolioManager) -> None:
        assert manager.can_trade("AAPL", quantity=0, price=150.0, side=OrderSide.BUY) is False
        assert manager.can_trade("AAPL", quantity=10, price=-1.0, side=OrderSide.BUY) is False

    def test_multiple_symbols(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY))
        manager.update_position(Trade(symbol="TSLA", quantity=5, price=200.0, side=OrderSide.BUY))

        portfolio = manager.get_portfolio()
        assert len(portfolio.positions) == 2
        assert portfolio.cash == 7500.0
        assert portfolio.total_value == 10000.0

    def test_realized_pnl_accumulation(self, manager: PortfolioManager) -> None:
        manager.update_position(Trade(symbol="AAPL", quantity=20, price=150.0, side=OrderSide.BUY))
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=160.0, side=OrderSide.SELL))
        manager.update_position(Trade(symbol="AAPL", quantity=10, price=170.0, side=OrderSide.SELL))

        assert manager.get_position("AAPL") is None
        portfolio = manager.get_portfolio()
        assert portfolio.total_pnl == 300.0
        assert portfolio.cash == 10300.0
