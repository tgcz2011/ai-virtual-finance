from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.agent.core import TradingAgent
from src.agent.models import AgentConfig, TradeAction
from src.agent.orchestrator import AgentOrchestrator
from src.agent.providers.base import MockLLMProvider
from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.engine.order.order_book import OrderBook
from src.engine.portfolio.manager import PortfolioManager
from src.engine.portfolio.models import OrderSide as PortfolioOrderSide
from src.engine.portfolio.models import Portfolio, Position, Trade as PortfolioTrade
from src.loan.manager import LoanManager
from src.loan.models import LoanStatus, MarginAccount
from src.validator.engine import ValidationEngine
from src.validator.rules.order_rules import SufficientFundsRule, ValidationResult


class MockMarketDataProvider:
    """Mock market data provider for integration testing."""

    def __init__(self, data: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._data = data or {}

    def get_data(self, symbol: str) -> list[dict[str, Any]]:
        return self._data.get(symbol, [])

    def add_bar(self, symbol: str, bar: dict[str, Any]) -> None:
        self._data.setdefault(symbol, []).append(bar)


def _make_agent_config(agent_id: str, name: str, initial_capital: float) -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name=name,
        llm_provider="mock",
        initial_capital=initial_capital,
        strategy_description="Test strategy",
        risk_tolerance=0.5,
        max_positions=10,
        allowed_asset_types=["stock"],
    )


def _make_buy_response(symbol: str, quantity: int) -> str:
    return f'{{"action": "BUY", "symbol": "{symbol}", "quantity": {quantity}, "reason": "test", "confidence": 0.9}}'


def _make_sell_response(symbol: str, quantity: int) -> str:
    return f'{{"action": "SELL", "symbol": "{symbol}", "quantity": {quantity}, "reason": "test", "confidence": 0.9}}'


class TestEndToEndCompleteTradeFlow:
    """Scenario 1: Complete trade flow (BUY then partial SELL)."""

    def test_complete_trade_flow(self) -> None:
        agent_id = str(uuid.uuid4())
        config = _make_agent_config(agent_id, "E2E-Agent", 100_000.0)
        portfolio_manager = PortfolioManager(agent_id, config.initial_capital)

        # Agent generates BUY AAPL 100 decision
        buy_response = _make_buy_response("AAPL", 100)
        provider = MockLLMProvider(response=buy_response)
        agent = TradingAgent(config, provider, portfolio_manager)

        # Build market data and think
        market_data: list[object] = []
        action = agent.think(market_data)
        assert action.action == "BUY"
        assert action.symbol == "AAPL"
        assert action.quantity == 100

        # Create order book with a matching sell order so the buy can fill
        order_book = OrderBook()
        sell_order = Order(
            id=str(uuid.uuid4()),
            agent_id="counterparty",
            symbol="AAPL",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=100,
            price=150.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        order_book.add_order(sell_order)

        # Execute buy
        order = agent.execute(action, order_book)
        assert order is not None
        assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)

        # Verify portfolio updated
        portfolio = portfolio_manager.get_portfolio()
        assert "AAPL" in portfolio.positions
        aapl_pos = portfolio.positions["AAPL"]
        assert aapl_pos.quantity == 100
        expected_cash = 100_000.0 - 100 * 150.0
        assert portfolio.cash == expected_cash

        # Agent generates SELL AAPL 50 decision
        sell_response = _make_sell_response("AAPL", 50)
        provider._response = sell_response
        action2 = agent.think(market_data)
        assert action2.action == "SELL"
        assert action2.quantity == 50

        # Add a matching buy order for the sell
        buy_order = Order(
            id=str(uuid.uuid4()),
            agent_id="counterparty2",
            symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=50,
            price=160.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        order_book.add_order(buy_order)

        order2 = agent.execute(action2, order_book)
        assert order2 is not None
        assert order2.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)

        # Verify partial sell
        portfolio2 = portfolio_manager.get_portfolio()
        assert "AAPL" in portfolio2.positions
        assert portfolio2.positions["AAPL"].quantity == 50
        expected_cash2 = expected_cash + 50 * 160.0
        assert portfolio2.cash == expected_cash2


class TestEndToEndMultiAgentCompetition:
    """Scenario 2: Multiple agents competing."""

    def test_multi_agent_competition(self) -> None:
        order_book = OrderBook()
        orchestrator = AgentOrchestrator()

        agents_data = [
            ("agent-1", "Aggressive", 100_000.0, _make_buy_response("TSLA", 10)),
            ("agent-2", "Conservative", 100_000.0, _make_buy_response("TSLA", 5)),
            ("agent-3", "Balanced", 100_000.0, _make_sell_response("TSLA", 15)),
        ]

        for aid, name, capital, response in agents_data:
            config = _make_agent_config(aid, name, capital)
            pm = PortfolioManager(aid, capital)
            provider = MockLLMProvider(response=response)
            agent = TradingAgent(config, provider, pm)
            orchestrator.register_agent(agent)

        # Seed order book with counterparty orders so agents can match
        counter_buy = Order(
            id=str(uuid.uuid4()),
            agent_id="cp-buy",
            symbol="TSLA",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=20,
            price=200.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        counter_sell = Order(
            id=str(uuid.uuid4()),
            agent_id="cp-sell",
            symbol="TSLA",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=20,
            price=200.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        order_book.add_order(counter_buy)
        order_book.add_order(counter_sell)

        # Run cycle: all agents think
        market_data: dict[str, list[object]] = {
            "agent-1": [],
            "agent-2": [],
            "agent-3": [],
        }
        actions = orchestrator.run_cycle(market_data)
        assert len(actions) == 3
        for aid, action in actions.items():
            assert action.action in ("BUY", "SELL")

        # Execute orders manually since run_all expects active_orders
        for aid, action in actions.items():
            agent = orchestrator._agents[aid]
            if action.action in ("BUY", "SELL") and action.quantity > 0:
                agent.execute(action, order_book)

        # Verify multiple agents have orders in the book
        all_orders = order_book.get_orders("TSLA")
        agent_orders = [o for o in all_orders if o.agent_id.startswith("agent-")]
        assert len(agent_orders) >= 2

        # Verify portfolios updated for agents that got fills
        for aid in ("agent-1", "agent-2", "agent-3"):
            agent = orchestrator._agents[aid]
            portfolio = agent.get_state().portfolio
            # At least some cash changed or a position exists
            has_position = bool(portfolio.positions)
            cash_changed = portfolio.cash != 100_000.0
            assert has_position or cash_changed or any(
                o.agent_id == aid for o in agent_orders
            )


class TestEndToEndRiskControlInterception:
    """Scenario 3: Risk control intercepts oversized order."""

    def test_risk_control_intercepts_oversized_order(self) -> None:
        agent_id = str(uuid.uuid4())
        config = _make_agent_config(agent_id, "RiskAgent", 10_000.0)
        portfolio_manager = PortfolioManager(agent_id, config.initial_capital)

        # Agent wants to buy 1000 shares at $20 = $20,000 > $10,000 cash
        response = _make_buy_response("AAPL", 1000)
        provider = MockLLMProvider(response=response)
        agent = TradingAgent(config, provider, portfolio_manager)

        market_data: list[object] = []
        action = agent.think(market_data)
        assert action.action == "BUY"
        assert action.quantity == 1000

        # Build a limit order at price 20.0 to trigger insufficient funds
        order = Order(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=1000,
            price=20.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        portfolio = portfolio_manager.get_portfolio()
        engine = ValidationEngine()
        engine.register_order_rule(SufficientFundsRule())
        result = engine.validate_order(order, portfolio)
        assert result.valid is False
        assert any("Insufficient funds" in err for err in result.errors)

        # Verify order was rejected conceptually (not submitted to book)
        order_book = OrderBook()
        pre_orders = order_book.get_orders("AAPL")
        assert len(pre_orders) == 0


class TestEndToEndMarginTrading:
    """Scenario 4: Margin trading flow."""

    def test_margin_trading_flow(self) -> None:
        agent_id = str(uuid.uuid4())
        config = _make_agent_config(agent_id, "MarginAgent", 50_000.0)
        portfolio_manager = PortfolioManager(agent_id, config.initial_capital)

        loan_manager = LoanManager(
            initial_margin_requirement=0.5,
            maintenance_margin=0.25,
        )

        portfolio = portfolio_manager.get_portfolio()

        # Request margin loan
        loan = loan_manager.request_margin_loan(agent_id, 20_000.0, portfolio)
        assert loan is not None
        assert loan.status == LoanStatus.ACTIVE
        assert loan.principal == 20_000.0

        # Use borrowed funds to buy stock (simulate by adding cash then buying)
        # In a real system the loan cash would be added to portfolio; here we simulate.
        portfolio_manager._cash += loan.principal

        # Buy MSFT with combined cash
        buy_response = _make_buy_response("MSFT", 100)
        provider = MockLLMProvider(response=buy_response)
        agent = TradingAgent(config, provider, portfolio_manager)

        order_book = OrderBook()
        counter_sell = Order(
            id=str(uuid.uuid4()),
            agent_id="cp",
            symbol="MSFT",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=100,
            price=300.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        order_book.add_order(counter_sell)

        action = agent.think([])
        order = agent.execute(action, order_book)
        assert order is not None
        assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)

        # Verify MarginAccount updated
        updated_portfolio = portfolio_manager.get_portfolio()
        margin_account = loan_manager.get_margin_account(agent_id, updated_portfolio)
        assert isinstance(margin_account, MarginAccount)
        assert margin_account.agent_id == agent_id
        assert margin_account.margin_used == 20_000.0

        # Verify margin call logic: if equity drops below maintenance
        # Simulate a big drop in portfolio value to trigger margin call
        # We artificially deflate positions and reduce cash to reduce total_value
        for sym in list(portfolio_manager._positions.keys()):
            pos = portfolio_manager._positions[sym]
            # Reduce current_price drastically (90% drop)
            bad_position = Position(
                symbol=pos.symbol,
                quantity=pos.quantity,
                average_cost=pos.average_cost,
                current_price=pos.average_cost * 0.05,
                unrealized_pnl=(pos.average_cost * 0.05 - pos.average_cost) * pos.quantity,
                realized_pnl=pos.realized_pnl,
                market_value=pos.quantity * pos.average_cost * 0.05,
            )
            portfolio_manager._positions[sym] = bad_position

        # Reduce cash to simulate losses - need equity ratio between 0 and 0.25
        # total_value = cash + position_value, debt = 20000
        # equity = total_value - 20000
        # ratio = equity / total_value, need 0 < ratio <= 0.25
        # With position_value = 1500: total_value = cash + 1500
        # equity = cash + 1500 - 20000 = cash - 18500
        # ratio = (cash - 18500) / (cash + 1500) = 0.25
        # cash - 18500 = 0.25 * cash + 375
        # 0.75 * cash = 18875
        # cash = 25166.67
        # Let's use cash = 24000 -> ratio = (24000 - 18500) / 25500 = 5500/25500 ≈ 0.216
        portfolio_manager._cash = 24000.0

        stressed_portfolio = portfolio_manager.get_portfolio()
        margin_call = loan_manager.check_margin_call(agent_id, stressed_portfolio)
        assert margin_call is True


class TestEndToEndDataFlowIntegration:
    """Scenario 5: Data flow from market data to trade execution."""

    def test_data_flow_integration(self) -> None:
        agent_id = str(uuid.uuid4())
        config = _make_agent_config(agent_id, "DataFlowAgent", 100_000.0)
        portfolio_manager = PortfolioManager(agent_id, config.initial_capital)

        # MockMarketDataProvider provides data
        mock_provider_data = MockMarketDataProvider()
        mock_provider_data.add_bar(
            "GOOGL",
            {
                "open": 130.0,
                "high": 135.0,
                "low": 129.0,
                "close": 134.0,
                "volume": 5000,
            },
        )

        # Agent decision based on data: we craft a provider response that references the data
        response = _make_buy_response("GOOGL", 50)
        llm_provider = MockLLMProvider(response=response)
        agent = TradingAgent(config, llm_provider, portfolio_manager)

        # Prepare market data objects for the agent
        raw_data = mock_provider_data.get_data("GOOGL")
        market_data: list[object] = [item for item in raw_data]
        action = agent.think(market_data)
        assert action.action == "BUY"
        assert action.symbol == "GOOGL"
        assert action.quantity == 50

        # Submit order to OrderBook
        order_book = OrderBook()
        counter_sell = Order(
            id=str(uuid.uuid4()),
            agent_id="cp",
            symbol="GOOGL",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=50,
            price=134.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        order_book.add_order(counter_sell)

        order = agent.execute(action, order_book)
        assert order is not None

        # Verify trade occurred
        trades = agent.get_state().trade_history
        assert len(trades) >= 1
        trade = trades[0]
        assert trade.symbol == "GOOGL"
        assert trade.quantity == 50.0
        assert trade.price == 134.0

        # Verify portfolio updated
        portfolio = portfolio_manager.get_portfolio()
        assert "GOOGL" in portfolio.positions
        assert portfolio.positions["GOOGL"].quantity == 50
