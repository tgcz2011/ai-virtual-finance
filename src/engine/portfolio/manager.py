from __future__ import annotations

from src.engine.portfolio.models import OrderSide, Portfolio, Position, Trade


class PortfolioManager:
    def __init__(self, agent_id: str, initial_cash: float) -> None:
        self._agent_id: str = agent_id
        self._cash: float = initial_cash
        self._positions: dict[str, Position] = {}
        self._total_realized_pnl: float = 0.0

    def update_position(self, trade: Trade) -> None:
        symbol = trade.symbol
        qty = trade.quantity
        price = trade.price
        side = trade.side

        existing = self._positions.get(symbol)

        if side == OrderSide.BUY:
            if existing is None:
                new_position = Position(
                    symbol=symbol,
                    quantity=qty,
                    average_cost=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    market_value=qty * price,
                )
                self._positions[symbol] = new_position
            else:
                total_cost = existing.average_cost * existing.quantity + price * qty
                new_qty = existing.quantity + qty
                new_avg_cost = total_cost / new_qty
                new_position = Position(
                    symbol=symbol,
                    quantity=new_qty,
                    average_cost=new_avg_cost,
                    current_price=price,
                    unrealized_pnl=(price - new_avg_cost) * new_qty,
                    realized_pnl=existing.realized_pnl,
                    market_value=new_qty * price,
                )
                self._positions[symbol] = new_position
            self._cash -= qty * price

        elif side == OrderSide.SELL:
            if existing is None or existing.quantity < qty:
                raise ValueError(f"Insufficient position to sell {qty} shares of {symbol}")

            realized = (price - existing.average_cost) * qty
            new_qty = existing.quantity - qty

            if new_qty == 0:
                self._total_realized_pnl += existing.realized_pnl + realized
                del self._positions[symbol]
            else:
                new_position = Position(
                    symbol=symbol,
                    quantity=new_qty,
                    average_cost=existing.average_cost,
                    current_price=price,
                    unrealized_pnl=(price - existing.average_cost) * new_qty,
                    realized_pnl=existing.realized_pnl + realized,
                    market_value=new_qty * price,
                )
                self._positions[symbol] = new_position
            self._cash += qty * price

    def get_portfolio(self) -> Portfolio:
        total_value = self._cash + sum(pos.market_value for pos in self._positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self._positions.values())
        positions_realized_pnl = sum(pos.realized_pnl for pos in self._positions.values())
        total_pnl = unrealized_pnl + positions_realized_pnl + self._total_realized_pnl
        return Portfolio(
            agent_id=self._agent_id,
            cash=self._cash,
            positions=dict(self._positions),
            total_value=total_value,
            total_pnl=total_pnl,
        )

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)

    def mark_to_market(self, prices: dict[str, float]) -> Portfolio:
        for symbol, price in prices.items():
            pos = self._positions.get(symbol)
            if pos is not None:
                new_position = Position(
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    average_cost=pos.average_cost,
                    current_price=price,
                    unrealized_pnl=(price - pos.average_cost) * pos.quantity,
                    realized_pnl=pos.realized_pnl,
                    market_value=pos.quantity * price,
                )
                self._positions[symbol] = new_position
        return self.get_portfolio()

    def can_trade(self, symbol: str, quantity: int, price: float, side: OrderSide) -> bool:
        if quantity <= 0 or price <= 0:
            return False
        if side == OrderSide.BUY:
            return self._cash >= quantity * price
        if side == OrderSide.SELL:
            pos = self._positions.get(symbol)
            return pos is not None and pos.quantity >= quantity
        return False
