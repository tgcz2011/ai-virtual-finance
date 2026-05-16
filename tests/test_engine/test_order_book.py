from __future__ import annotations

import pytest

from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.engine.order.order_book import OrderBook


def make_order(
    order_id: str,
    side: OrderSide,
    order_type: OrderType,
    quantity: float,
    price: float | None = None,
    symbol: str = "AAPL",
    agent_id: str = "agent1",
) -> Order:
    return Order(
        id=order_id,
        agent_id=agent_id,
        symbol=symbol,
        side=side,
        type=order_type,
        quantity=quantity,
        price=price,
    )


class TestOrderBook:
    def test_market_order_immediate_fill(self) -> None:
        book = OrderBook()
        sell = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 10, 100.0)
        book.add_order(sell)

        buy = make_order("buy1", OrderSide.BUY, OrderType.MARKET, 10)
        trades = book.add_order(buy)

        assert len(trades) == 1
        assert trades[0].quantity == 10.0
        assert trades[0].price == 100.0
        assert buy.status == OrderStatus.FILLED
        assert sell.status == OrderStatus.FILLED

    def test_limit_order_rest_on_book(self) -> None:
        book = OrderBook()
        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 99.0)
        trades = book.add_order(buy)

        assert len(trades) == 0
        assert buy.status == OrderStatus.OPEN
        bids = book.get_bids("AAPL")
        assert len(bids) == 1
        assert bids[0].id == "buy1"

    def test_price_priority_matching(self) -> None:
        book = OrderBook()
        sell1 = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 5, 101.0)
        sell2 = make_order("sell2", OrderSide.SELL, OrderType.LIMIT, 5, 100.0)
        book.add_order(sell1)
        book.add_order(sell2)

        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 5, 100.0)
        trades = book.add_order(buy)

        assert len(trades) == 1
        # Should match with lower price first (price priority)
        assert trades[0].price == 100.0
        assert trades[0].sell_order_id == "sell2"
        assert sell2.status == OrderStatus.FILLED
        assert sell1.status == OrderStatus.OPEN

    def test_time_priority_matching(self) -> None:
        book = OrderBook()
        sell1 = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 5, 100.0)
        sell2 = make_order("sell2", OrderSide.SELL, OrderType.LIMIT, 5, 100.0)
        book.add_order(sell1)
        book.add_order(sell2)

        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 5, 100.0)
        trades = book.add_order(buy)

        assert len(trades) == 1
        # Same price: earlier order should match first (time priority)
        assert trades[0].sell_order_id == "sell1"
        assert sell1.status == OrderStatus.FILLED
        assert sell2.status == OrderStatus.OPEN

    def test_partial_fill(self) -> None:
        book = OrderBook()
        sell = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 3, 100.0)
        book.add_order(sell)

        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        trades = book.add_order(buy)

        assert len(trades) == 1
        assert trades[0].quantity == 3.0
        assert sell.status == OrderStatus.FILLED
        assert buy.status == OrderStatus.PARTIALLY_FILLED
        assert buy.filled_quantity == 3.0
        assert buy.remaining_quantity() == 7.0

    def test_cancel_order(self) -> None:
        book = OrderBook()
        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        book.add_order(buy)

        assert book.cancel_order("buy1") is True
        assert buy.status == OrderStatus.CANCELLED
        assert book.cancel_order("buy1") is False
        assert book.cancel_order("nonexistent") is False

    def test_buy_sell_match(self) -> None:
        book = OrderBook()
        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        sell = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 10, 100.0)
        book.add_order(buy)
        trades = book.add_order(sell)

        assert len(trades) == 1
        trade = trades[0]
        assert trade.buy_order_id == "buy1"
        assert trade.sell_order_id == "sell1"
        assert trade.quantity == 10.0
        assert trade.price == 100.0
        assert buy.status == OrderStatus.FILLED
        assert sell.status == OrderStatus.FILLED

    def test_get_orders_filter_by_symbol(self) -> None:
        book = OrderBook()
        aapl = make_order("aapl1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0, symbol="AAPL")
        tsla = make_order("tsla1", OrderSide.BUY, OrderType.LIMIT, 5, 200.0, symbol="TSLA")
        book.add_order(aapl)
        book.add_order(tsla)

        all_orders = book.get_orders()
        assert len(all_orders) == 2

        aapl_orders = book.get_orders("AAPL")
        assert len(aapl_orders) == 1
        assert aapl_orders[0].symbol == "AAPL"

    def test_get_bids_and_asks(self) -> None:
        book = OrderBook()
        buy1 = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        buy2 = make_order("buy2", OrderSide.BUY, OrderType.LIMIT, 5, 101.0)
        sell1 = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 5, 102.0)
        book.add_order(buy1)
        book.add_order(buy2)
        book.add_order(sell1)

        bids = book.get_bids("AAPL")
        assert len(bids) == 2
        assert bids[0].price == 101.0  # Higher price first
        assert bids[1].price == 100.0

        asks = book.get_asks("AAPL")
        assert len(asks) == 1
        assert asks[0].price == 102.0

    def test_multiple_trades_single_order(self) -> None:
        book = OrderBook()
        sell1 = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 3, 100.0)
        sell2 = make_order("sell2", OrderSide.SELL, OrderType.LIMIT, 3, 100.0)
        book.add_order(sell1)
        book.add_order(sell2)

        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 6, 100.0)
        trades = book.add_order(buy)

        assert len(trades) == 2
        assert buy.status == OrderStatus.FILLED
        assert sell1.status == OrderStatus.FILLED
        assert sell2.status == OrderStatus.FILLED

    def test_market_order_no_match(self) -> None:
        book = OrderBook()
        buy = make_order("buy1", OrderSide.BUY, OrderType.MARKET, 10)
        trades = book.add_order(buy)

        assert len(trades) == 0
        assert buy.status == OrderStatus.REJECTED

    def test_cancel_filled_order_fails(self) -> None:
        book = OrderBook()
        sell = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 10, 100.0)
        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        book.add_order(sell)
        book.add_order(buy)

        assert sell.status == OrderStatus.FILLED
        assert book.cancel_order("sell1") is False

    def test_average_price_calculation(self) -> None:
        book = OrderBook()
        sell1 = make_order("sell1", OrderSide.SELL, OrderType.LIMIT, 5, 100.0)
        sell2 = make_order("sell2", OrderSide.SELL, OrderType.LIMIT, 5, 110.0)
        book.add_order(sell1)
        book.add_order(sell2)

        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 110.0)
        book.add_order(buy)

        assert buy.filled_quantity == 10.0
        expected_avg = (5 * 100.0 + 5 * 110.0) / 10.0
        assert buy.average_price == pytest.approx(expected_avg)

    def test_add_cancelled_order_returns_empty(self) -> None:
        book = OrderBook()
        buy = make_order("buy1", OrderSide.BUY, OrderType.LIMIT, 10, 100.0)
        buy.status = OrderStatus.CANCELLED
        trades = book.add_order(buy)
        assert trades == []
