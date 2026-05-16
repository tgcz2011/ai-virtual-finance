from __future__ import annotations

import json

import pytest

from src.agent.core import TradingAgent
from src.agent.models import AgentConfig, TradeAction
from src.agent.orchestrator import AgentOrchestrator
from src.agent.providers.base import MockLLMProvider
from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType
from src.engine.order.order_book import OrderBook
from src.engine.portfolio.manager import PortfolioManager


@pytest.fixture
def orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator()


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        id="agent-001",
        name="TestAgent",
        llm_provider="mock",
        initial_capital=100000.0,
        strategy_description="Test strategy",
        risk_tolerance=0.5,
        max_positions=10,
        allowed_asset_types=["stock"],
    )


@pytest.fixture
def agent(agent_config: AgentConfig) -> TradingAgent:
    pm = PortfolioManager(agent_id=agent_config.id, initial_cash=agent_config.initial_capital)
    provider = MockLLMProvider(response=json.dumps({
        "action": "BUY",
        "symbol": "AAPL",
        "quantity": 10,
        "reason": "Test",
        "confidence": 0.9,
    }))
    return TradingAgent(config=agent_config, llm_provider=provider, portfolio_manager=pm)


class TestAgentOrchestrator:
    def test_register_agent(self, orchestrator: AgentOrchestrator, agent: TradingAgent) -> None:
        orchestrator.register_agent(agent)
        assert "agent-001" in orchestrator._agents

    def test_run_cycle(self, orchestrator: AgentOrchestrator, agent: TradingAgent) -> None:
        orchestrator.register_agent(agent)
        market_data = {"agent-001": ["AAPL: 150.0"]}
        results = orchestrator.run_cycle(market_data)
        assert "agent-001" in results
        assert results["agent-001"].action == "BUY"

    def test_run_cycle_empty_agents(self, orchestrator: AgentOrchestrator) -> None:
        results = orchestrator.run_cycle({})
        assert results == {}

    def test_run_all(self, orchestrator: AgentOrchestrator, agent: TradingAgent) -> None:
        order_book = OrderBook()
        orchestrator.register_agent(agent)
        action = TradeAction(action="BUY", symbol="AAPL", quantity=10)
        agent.execute(action, order_book)

        results = orchestrator.run_all(order_book)
        assert "agent-001" in results

    def test_run_all_no_active_orders(self, orchestrator: AgentOrchestrator, agent: TradingAgent) -> None:
        order_book = OrderBook()
        orchestrator.register_agent(agent)
        results = orchestrator.run_all(order_book)
        assert results.get("agent-001") == []

    def test_multiple_agents(self, orchestrator: AgentOrchestrator) -> None:
        configs = [
            AgentConfig(
                id=f"agent-{i:03d}",
                name=f"Agent{i}",
                llm_provider="mock",
                initial_capital=100000.0,
                strategy_description="Test",
                risk_tolerance=0.5,
                max_positions=10,
                allowed_asset_types=["stock"],
            )
            for i in range(3)
        ]
        for config in configs:
            pm = PortfolioManager(agent_id=config.id, initial_cash=config.initial_capital)
            provider = MockLLMProvider(response=json.dumps({
                "action": "BUY",
                "symbol": "AAPL",
                "quantity": 1,
                "reason": "Test",
                "confidence": 0.5,
            }))
            agent = TradingAgent(config=config, llm_provider=provider, portfolio_manager=pm)
            orchestrator.register_agent(agent)

        market_data = {c.id: ["AAPL: 150.0"] for c in configs}
        results = orchestrator.run_cycle(market_data)
        assert len(results) == 3
        for config in configs:
            assert config.id in results
