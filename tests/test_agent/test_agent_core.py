from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.agent.core import TradingAgent
from src.agent.models import AgentConfig, AgentStatus, TradeAction
from src.agent.providers.base import MockLLMProvider
from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.engine.order.order_book import OrderBook
from src.engine.portfolio.manager import PortfolioManager


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        id="agent-001",
        name="TestAgent",
        llm_provider="mock",
        initial_capital=100000.0,
        strategy_description="Buy low, sell high",
        risk_tolerance=0.5,
        max_positions=10,
        allowed_asset_types=["stock"],
    )


@pytest.fixture
def portfolio_manager(agent_config: AgentConfig) -> PortfolioManager:
    return PortfolioManager(agent_id=agent_config.id, initial_cash=agent_config.initial_capital)


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def agent(agent_config: AgentConfig, mock_provider: MockLLMProvider, portfolio_manager: PortfolioManager) -> TradingAgent:
    return TradingAgent(config=agent_config, llm_provider=mock_provider, portfolio_manager=portfolio_manager)


class TestTradingAgentThink:
    def test_think_returns_hold_by_default(self, agent: TradingAgent) -> None:
        action = agent.think([])
        assert action.action == "HOLD"

    def test_think_with_buy_response(self, agent_config: AgentConfig, portfolio_manager: PortfolioManager) -> None:
        response = json.dumps({
            "action": "BUY",
            "symbol": "AAPL",
            "quantity": 10,
            "reason": "Looks good",
            "confidence": 0.9,
        })
        provider = MockLLMProvider(response=response)
        agent = TradingAgent(config=agent_config, llm_provider=provider, portfolio_manager=portfolio_manager)
        action = agent.think([])
        assert action.action == "BUY"
        assert action.symbol == "AAPL"
        assert action.quantity == 10
        assert action.confidence == pytest.approx(0.9)

    def test_think_with_sell_response(self, agent_config: AgentConfig, portfolio_manager: PortfolioManager) -> None:
        response = json.dumps({
            "action": "SELL",
            "symbol": "TSLA",
            "quantity": 5,
            "reason": "Profit taking",
            "confidence": 0.8,
        })
        provider = MockLLMProvider(response=response)
        agent = TradingAgent(config=agent_config, llm_provider=provider, portfolio_manager=portfolio_manager)
        action = agent.think([])
        assert action.action == "SELL"
        assert action.symbol == "TSLA"

    def test_think_with_markdown_json(self, agent_config: AgentConfig, portfolio_manager: PortfolioManager) -> None:
        response = "```json\n" + json.dumps({
            "action": "BUY",
            "symbol": "MSFT",
            "quantity": 3,
            "reason": "Growth",
            "confidence": 0.7,
        }) + "\n```"
        provider = MockLLMProvider(response=response)
        agent = TradingAgent(config=agent_config, llm_provider=provider, portfolio_manager=portfolio_manager)
        action = agent.think([])
        assert action.action == "BUY"
        assert action.symbol == "MSFT"

    def test_think_invalid_json(self, agent: TradingAgent) -> None:
        provider = MockLLMProvider(response="not json")
        agent._llm_provider = provider
        action = agent.think([])
        assert action.action == "HOLD"
        assert "Error" in action.reason

    def test_think_while_paused(self, agent: TradingAgent) -> None:
        agent.pause()
        action = agent.think([])
        assert action.action == "HOLD"
        assert "paused" in action.reason.lower()


class TestTradingAgentExecute:
    def test_execute_hold_returns_none(self, agent: TradingAgent) -> None:
        order_book = OrderBook()
        action = TradeAction(action="HOLD", symbol="AAPL", quantity=0)
        result = agent.execute(action, order_book)
        assert result is None

    def test_execute_buy(self, agent: TradingAgent) -> None:
        order_book = OrderBook()
        action = TradeAction(action="BUY", symbol="AAPL", quantity=10)
        result = agent.execute(action, order_book)
        assert result is not None
        assert result.side == OrderSide.BUY
        assert result.symbol == "AAPL"
        assert result.quantity == 10

    def test_execute_sell(self, agent: TradingAgent) -> None:
        order_book = OrderBook()
        action = TradeAction(action="SELL", symbol="AAPL", quantity=5)
        result = agent.execute(action, order_book)
        assert result is not None
        assert result.side == OrderSide.SELL

    def test_execute_while_paused(self, agent: TradingAgent) -> None:
        order_book = OrderBook()
        agent.pause()
        action = TradeAction(action="BUY", symbol="AAPL", quantity=10)
        result = agent.execute(action, order_book)
        assert result is None


class TestTradingAgentState:
    def test_get_state(self, agent: TradingAgent) -> None:
        state = agent.get_state()
        assert state.config.id == "agent-001"
        assert state.status == AgentStatus.IDLE
        assert state.portfolio.cash == pytest.approx(100000.0)

    def test_pause_resume(self, agent: TradingAgent) -> None:
        agent.pause()
        assert agent.get_state().status == AgentStatus.PAUSED
        agent.resume()
        assert agent.get_state().status == AgentStatus.IDLE


class TestPortfolioTrade:
    def test_portfolio_trade_creation(self) -> None:
        from src.engine.portfolio.models import Trade as PortfolioTrade
        trade = PortfolioTrade(symbol="AAPL", quantity=10, price=150.0, side="buy")
        assert trade.symbol == "AAPL"
        assert trade.quantity == 10
        assert trade.price == pytest.approx(150.0)
        assert trade.side.value == "buy"
