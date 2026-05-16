from __future__ import annotations

import concurrent.futures
from typing import TYPE_CHECKING

from src.agent.models import TradeAction
from src.engine.order.models import Trade

if TYPE_CHECKING:
    from src.agent.core import TradingAgent
    from src.engine.order.order_book import OrderBook


class AgentOrchestrator:
    """Orchestrates multiple trading agents."""

    def __init__(self) -> None:
        self._agents: dict[str, TradingAgent] = {}

    def register_agent(self, agent: TradingAgent) -> None:
        """Register a trading agent."""
        self._agents[agent._config.id] = agent

    def run_cycle(self, market_data: dict[str, list[object]]) -> dict[str, TradeAction]:
        """Run a single thinking cycle for all agents.

        Returns a mapping of agent_id -> TradeAction.
        """
        results: dict[str, TradeAction] = {}

        def _think(agent_id: str, agent: TradingAgent) -> tuple[str, TradeAction]:
            data = market_data.get(agent_id, [])
            action = agent.think(data)
            return agent_id, action

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(_think, aid, agent): aid
                for aid, agent in self._agents.items()
            }
            for future in concurrent.futures.as_completed(futures):
                agent_id, action = future.result()
                results[agent_id] = action

        return results

    def run_all(self, order_book: OrderBook) -> dict[str, list[Trade]]:
        """Run all agents to execute their current intended actions.

        This is a simplified version that assumes each agent already has a
        pending action. For a full loop, use run_cycle first.

        Returns a mapping of agent_id -> list of trades.
        """
        results: dict[str, list[Trade]] = {}

        for agent_id, agent in self._agents.items():
            state = agent.get_state()
            agent_trades: list[Trade] = []
            for order in state.active_orders:
                if order.is_active():
                    trades = order_book.add_order(order)
                    agent_trades.extend(trades)
            results[agent_id] = agent_trades

        return results
