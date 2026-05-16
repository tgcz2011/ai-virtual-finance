from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from src.agent.models import AgentConfig, AgentState, AgentStatus, TradeAction
from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.engine.portfolio.models import Trade as PortfolioTradeModel

if TYPE_CHECKING:
    from src.agent.providers.base import LLMProvider
    from src.engine.order.order_book import OrderBook
    from src.engine.portfolio.manager import PortfolioManager


class TradingAgent:
    """AI trading agent that uses an LLM provider to make trading decisions."""

    def __init__(
        self,
        config: AgentConfig,
        llm_provider: LLMProvider,
        portfolio_manager: PortfolioManager,
    ) -> None:
        self._config = config
        self._llm_provider = llm_provider
        self._portfolio_manager = portfolio_manager
        self._status = AgentStatus.IDLE
        self._active_orders: list[Order] = []
        self._trade_history: list[Trade] = []
        self._paused = False

    def _build_prompt(self, market_data: list[object]) -> str:
        """Build a trading prompt for the LLM."""
        portfolio = self._portfolio_manager.get_portfolio()
        positions_str = "\n".join(
            f"- {sym}: qty={pos.quantity}, avg_cost={pos.average_cost}, current={pos.current_price}"
            for sym, pos in portfolio.positions.items()
        ) or "No open positions."

        market_str = "\n".join(str(md) for md in market_data)

        trade_history_str = "\n".join(
            f"- {t.symbol}: {t.quantity} @ {t.price}"
            for t in self._trade_history[-10:]
        ) or "No recent trades."

        prompt = f"""You are an AI trading agent.

Strategy: {self._config.strategy_description}
Risk Tolerance: {self._config.risk_tolerance}
Max Positions: {self._config.max_positions}
Allowed Assets: {', '.join(self._config.allowed_asset_types) or 'All'}

Current Portfolio:
Cash: {portfolio.cash:.2f}
Positions:
{positions_str}

Market Data:
{market_str}

Recent Trade History:
{trade_history_str}

Based on the above, decide your next action.
Respond ONLY with a JSON object in this exact format:
{{"action": "BUY|SELL|HOLD", "symbol": "SYM", "quantity": 0, "reason": "...", "confidence": 0.0}}
"""
        return prompt

    def think(self, market_data: list[object]) -> TradeAction:
        """Generate a trading decision using the LLM provider."""
        if self._paused:
            return TradeAction(action="HOLD", symbol="", quantity=0, reason="Agent is paused", confidence=0.0)

        self._status = AgentStatus.THINKING
        try:
            prompt = self._build_prompt(market_data)
            response = self._llm_provider.generate(prompt)
            action = self._parse_response(response)
            self._status = AgentStatus.IDLE
            return action
        except Exception as exc:
            self._status = AgentStatus.ERROR
            return TradeAction(action="HOLD", symbol="", quantity=0, reason=f"Error: {exc}", confidence=0.0)

    def _parse_response(self, response: str) -> TradeAction:
        """Parse LLM JSON response into a TradeAction."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response: {exc}") from exc

        return TradeAction(
            action=data.get("action", "HOLD"),
            symbol=data.get("symbol", ""),
            quantity=int(data.get("quantity", 0)),
            reason=data.get("reason", ""),
            confidence=float(data.get("confidence", 0.0)),
        )

    def execute(self, action: TradeAction, order_book: OrderBook) -> Order | None:
        """Execute a trade action on the order book."""
        if action.action == "HOLD" or action.quantity <= 0:
            return None

        if self._paused:
            return None

        self._status = AgentStatus.TRADING

        side = OrderSide.BUY if action.action == "BUY" else OrderSide.SELL
        order = Order(
            id=str(uuid.uuid4()),
            agent_id=self._config.id,
            symbol=action.symbol,
            side=side,
            type=OrderType.MARKET,
            quantity=action.quantity,
            price=None,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        trades = order_book.add_order(order)
        self._active_orders.append(order)

        for trade in trades:
            self._trade_history.append(trade)
            from src.engine.portfolio.models import OrderSide as PortfolioOrderSide
            portfolio_side = PortfolioOrderSide.BUY if side == OrderSide.BUY else PortfolioOrderSide.SELL
            portfolio_trade = PortfolioTradeModel(
                symbol=trade.symbol,
                quantity=int(trade.quantity),
                price=trade.price,
                side=portfolio_side,
            )
            self._portfolio_manager.update_position(portfolio_trade)

        self._status = AgentStatus.IDLE
        return order

    def get_state(self) -> AgentState:
        """Return the current agent state."""
        return AgentState(
            config=self._config,
            portfolio=self._portfolio_manager.get_portfolio(),
            active_orders=list(self._active_orders),
            trade_history=list(self._trade_history),
            status=self._status,
        )

    def pause(self) -> None:
        """Pause the agent."""
        self._paused = True
        self._status = AgentStatus.PAUSED

    def resume(self) -> None:
        """Resume the agent."""
        self._paused = False
        self._status = AgentStatus.IDLE
