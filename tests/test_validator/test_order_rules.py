from __future__ import annotations

from datetime import time
from unittest.mock import patch

import pytest

from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType
from src.engine.portfolio.models import Portfolio, Position
from src.validator.engine import ValidationEngine
from src.validator.rules.order_rules import (
    MarketHoursRule,
    OrderSizeRule,
    PositionLimitRule,
    PriceLimitRule,
    SufficientFundsRule,
    ValidationResult,
)


@pytest.fixture
def portfolio() -> Portfolio:
    return Portfolio(
        agent_id="test-agent",
        cash=100000.0,
        positions={},
        total_value=100000.0,
        total_pnl=0.0,
    )


@pytest.fixture
def portfolio_with_position() -> Portfolio:
    position = Position(
        symbol="AAPL",
        quantity=100,
        average_cost=100.0,
        current_price=150.0,
        unrealized_pnl=5000.0,
        realized_pnl=0.0,
        market_value=15000.0,
    )
    return Portfolio(
        agent_id="test-agent",
        cash=85000.0,
        positions={"AAPL": position},
        total_value=100000.0,
        total_pnl=5000.0,
    )


@pytest.fixture
def buy_order() -> Order:
    return Order(
        id="order-1",
        agent_id="test-agent",
        symbol="AAPL",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        quantity=10,
        price=100.0,
        status=OrderStatus.PENDING,
    )


@pytest.fixture
def sell_order() -> Order:
    return Order(
        id="order-2",
        agent_id="test-agent",
        symbol="AAPL",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        quantity=10,
        price=100.0,
        status=OrderStatus.PENDING,
    )


class TestValidationResult:
    def test_valid_result(self) -> None:
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result(self) -> None:
        result = ValidationResult(valid=False, errors=["error1", "error2"])
        assert result.valid is False
        assert result.errors == ["error1", "error2"]


class TestSufficientFundsRule:
    def test_sufficient_funds(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = SufficientFundsRule()
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_insufficient_funds(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = SufficientFundsRule()
        buy_order.price = 20000.0
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "Insufficient funds" in result.errors[0]

    def test_sell_order_ignored(self, portfolio: Portfolio, sell_order: Order) -> None:
        rule = SufficientFundsRule()
        result = rule.validate(sell_order, portfolio)
        assert result.valid is True

    def test_market_order_no_price(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = SufficientFundsRule()
        buy_order.price = None
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True


class TestPositionLimitRule:
    def test_within_limit(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PositionLimitRule(max_position_ratio=0.30)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_exceeds_limit(self, portfolio_with_position: Portfolio, buy_order: Order) -> None:
        rule = PositionLimitRule(max_position_ratio=0.30)
        buy_order.quantity = 2000
        result = rule.validate(buy_order, portfolio_with_position)
        assert result.valid is False
        assert "Position limit exceeded" in result.errors[0]

    def test_sell_order_ignored(self, portfolio_with_position: Portfolio, sell_order: Order) -> None:
        rule = PositionLimitRule(max_position_ratio=0.30)
        result = rule.validate(sell_order, portfolio_with_position)
        assert result.valid is True

    def test_zero_portfolio_value(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PositionLimitRule(max_position_ratio=0.30)
        portfolio = portfolio.model_copy(update={"total_value": 0.0})
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "positive" in result.errors[0]


class TestOrderSizeRule:
    def test_valid_size(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(min_quantity=1.0, max_quantity=100.0)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_below_minimum(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(min_quantity=20.0)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "below minimum" in result.errors[0]

    def test_above_maximum(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(max_quantity=5.0)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "above maximum" in result.errors[0]

    def test_notional_too_large(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(max_notional=500.0)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "notional" in result.errors[0]

    def test_multiple_errors(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(min_quantity=20.0, max_notional=500.0)
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert len(result.errors) == 2

    def test_no_price_skips_notional(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = OrderSizeRule(max_notional=500.0)
        buy_order.price = None
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True


class TestPriceLimitRule:
    def test_within_limit(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PriceLimitRule(
            price_limit_ratio=0.10,
            reference_prices={"AAPL": 100.0},
        )
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_above_upper_limit(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PriceLimitRule(
            price_limit_ratio=0.10,
            reference_prices={"AAPL": 50.0},
        )
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "above upper limit" in result.errors[0]

    def test_below_lower_limit(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PriceLimitRule(
            price_limit_ratio=0.10,
            reference_prices={"AAPL": 200.0},
        )
        result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "below lower limit" in result.errors[0]

    def test_no_reference_price(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PriceLimitRule(reference_prices={})
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_no_order_price(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = PriceLimitRule(reference_prices={"AAPL": 100.0})
        buy_order.price = None
        result = rule.validate(buy_order, portfolio)
        assert result.valid is True


class TestMarketHoursRule:
    def test_within_market_hours(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = MarketHoursRule(market_open=time(9, 0), market_close=time(17, 0))
        with patch("src.validator.rules.order_rules.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(10, 0)
            result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_outside_market_hours(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = MarketHoursRule(market_open=time(9, 0), market_close=time(17, 0))
        with patch("src.validator.rules.order_rules.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(18, 0)
            result = rule.validate(buy_order, portfolio)
        assert result.valid is False
        assert "Market is closed" in result.errors[0]

    def test_pre_market_allowed(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = MarketHoursRule(
            market_open=time(9, 30),
            market_close=time(15, 0),
            check_pre_market=True,
        )
        with patch("src.validator.rules.order_rules.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(9, 20)
            result = rule.validate(buy_order, portfolio)
        assert result.valid is True

    def test_pre_market_not_allowed(self, portfolio: Portfolio, buy_order: Order) -> None:
        rule = MarketHoursRule(
            market_open=time(9, 30),
            market_close=time(15, 0),
            check_pre_market=False,
        )
        with patch("src.validator.rules.order_rules.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(9, 20)
            result = rule.validate(buy_order, portfolio)
        assert result.valid is False


class TestValidationEngine:
    def test_register_and_validate_order(self, portfolio: Portfolio, buy_order: Order) -> None:
        engine = ValidationEngine()
        engine.register_order_rule(SufficientFundsRule())
        engine.register_order_rule(OrderSizeRule(max_quantity=50.0))

        result = engine.validate_order(buy_order, portfolio)
        assert result.valid is True

    def test_short_circuit(self, portfolio: Portfolio, buy_order: Order) -> None:
        engine = ValidationEngine()
        engine.register_order_rule(SufficientFundsRule())
        engine.register_order_rule(OrderSizeRule(max_quantity=5.0))

        buy_order.price = 20000.0
        result = engine.validate_order(buy_order, portfolio)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Insufficient funds" in result.errors[0]

    def test_no_short_circuit(self, portfolio: Portfolio, buy_order: Order) -> None:
        engine = ValidationEngine()
        engine.set_short_circuit(False)
        engine.register_order_rule(SufficientFundsRule())
        engine.register_order_rule(OrderSizeRule(max_quantity=5.0))

        buy_order.price = 20000.0
        result = engine.validate_order(buy_order, portfolio)
        assert result.valid is False
        assert len(result.errors) == 2

    def test_rule_priority_order(self, portfolio: Portfolio, buy_order: Order) -> None:
        engine = ValidationEngine()
        engine.register_order_rule(OrderSizeRule(max_quantity=5.0))
        engine.register_order_rule(SufficientFundsRule())

        result = engine.validate_order(buy_order, portfolio)
        assert result.valid is False
        assert "above maximum" in result.errors[0]

    def test_empty_engine(self, portfolio: Portfolio, buy_order: Order) -> None:
        engine = ValidationEngine()
        result = engine.validate_order(buy_order, portfolio)
        assert result.valid is True

    def test_risk_assessment(self, portfolio_with_position: Portfolio) -> None:
        from src.validator.rules.risk_rules import (
            ConcentrationRiskRule,
            DrawdownRiskRule,
            LeverageRiskRule,
        )

        engine = ValidationEngine()
        engine.register_risk_rule(ConcentrationRiskRule())
        engine.register_risk_rule(DrawdownRiskRule())
        engine.register_risk_rule(LeverageRiskRule())

        results = engine.assess_risk(portfolio_with_position, {})
        assert len(results) == 3
