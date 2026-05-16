from __future__ import annotations

import pytest

from src.engine.portfolio.models import Portfolio, Position
from src.validator.engine import ValidationEngine
from src.validator.rules.risk_rules import (
    ConcentrationRiskRule,
    DrawdownRiskRule,
    LeverageRiskRule,
    RiskLevel,
    RiskResult,
)


@pytest.fixture
def empty_portfolio() -> Portfolio:
    return Portfolio(
        agent_id="test-agent",
        cash=100000.0,
        positions={},
        total_value=100000.0,
        total_pnl=0.0,
    )


@pytest.fixture
def diversified_portfolio() -> Portfolio:
    pos1 = Position(
        symbol="AAPL",
        quantity=100,
        average_cost=100.0,
        current_price=150.0,
        unrealized_pnl=5000.0,
        realized_pnl=0.0,
        market_value=15000.0,
    )
    pos2 = Position(
        symbol="GOOGL",
        quantity=50,
        average_cost=200.0,
        current_price=250.0,
        unrealized_pnl=2500.0,
        realized_pnl=0.0,
        market_value=12500.0,
    )
    return Portfolio(
        agent_id="test-agent",
        cash=72500.0,
        positions={"AAPL": pos1, "GOOGL": pos2},
        total_value=100000.0,
        total_pnl=7500.0,
    )


@pytest.fixture
def concentrated_portfolio() -> Portfolio:
    position = Position(
        symbol="AAPL",
        quantity=500,
        average_cost=100.0,
        current_price=150.0,
        unrealized_pnl=25000.0,
        realized_pnl=0.0,
        market_value=75000.0,
    )
    return Portfolio(
        agent_id="test-agent",
        cash=25000.0,
        positions={"AAPL": position},
        total_value=100000.0,
        total_pnl=25000.0,
    )


@pytest.fixture
def leveraged_portfolio() -> Portfolio:
    position = Position(
        symbol="AAPL",
        quantity=200,
        average_cost=100.0,
        current_price=150.0,
        unrealized_pnl=10000.0,
        realized_pnl=0.0,
        market_value=30000.0,
    )
    return Portfolio(
        agent_id="test-agent",
        cash=-5000.0,
        positions={"AAPL": position},
        total_value=25000.0,
        total_pnl=10000.0,
    )


class TestRiskResult:
    def test_risk_result_low(self) -> None:
        result = RiskResult(level=RiskLevel.LOW, messages=["All good"])
        assert result.level == RiskLevel.LOW
        assert result.messages == ["All good"]

    def test_risk_result_critical(self) -> None:
        result = RiskResult(level=RiskLevel.CRITICAL, messages=["Danger"])
        assert result.level == RiskLevel.CRITICAL


class TestConcentrationRiskRule:
    def test_no_positions(self, empty_portfolio: Portfolio) -> None:
        rule = ConcentrationRiskRule()
        result = rule.evaluate(empty_portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "No positions held" in result.messages[0]

    def test_diversified(self, diversified_portfolio: Portfolio) -> None:
        rule = ConcentrationRiskRule(warning_threshold=0.30, critical_threshold=0.50)
        result = rule.evaluate(diversified_portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "Concentration OK" in result.messages[0]

    def test_high_concentration(self, diversified_portfolio: Portfolio) -> None:
        rule = ConcentrationRiskRule(warning_threshold=0.10, critical_threshold=0.50)
        result = rule.evaluate(diversified_portfolio, {})
        assert result.level == RiskLevel.HIGH
        assert "High concentration" in result.messages[0]

    def test_critical_concentration(self, concentrated_portfolio: Portfolio) -> None:
        rule = ConcentrationRiskRule(warning_threshold=0.20, critical_threshold=0.50)
        result = rule.evaluate(concentrated_portfolio, {})
        assert result.level == RiskLevel.CRITICAL
        assert "Critical concentration" in result.messages[0]

    def test_zero_portfolio_value(self, empty_portfolio: Portfolio) -> None:
        rule = ConcentrationRiskRule()
        portfolio = empty_portfolio.model_copy(update={"total_value": 0.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.CRITICAL
        assert "zero or negative" in result.messages[0]


class TestDrawdownRiskRule:
    def test_no_peak_yet(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule()
        portfolio = empty_portfolio.model_copy(update={"total_value": 0.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "No peak value" in result.messages[0]

    def test_no_drawdown(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule()
        rule._peak_value = 100000.0
        result = rule.evaluate(empty_portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "No drawdown" in result.messages[0]

    def test_moderate_drawdown(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule(warning_threshold=0.10, critical_threshold=0.20)
        rule._peak_value = 100000.0
        portfolio = empty_portfolio.model_copy(update={"total_value": 95000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.MEDIUM
        assert "Moderate drawdown" in result.messages[0]

    def test_high_drawdown(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule(warning_threshold=0.10, critical_threshold=0.20)
        rule._peak_value = 100000.0
        portfolio = empty_portfolio.model_copy(update={"total_value": 85000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.HIGH
        assert "High drawdown" in result.messages[0]

    def test_critical_drawdown(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule(warning_threshold=0.10, critical_threshold=0.20)
        rule._peak_value = 100000.0
        portfolio = empty_portfolio.model_copy(update={"total_value": 70000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.CRITICAL
        assert "Critical drawdown" in result.messages[0]

    def test_peak_updates(self, empty_portfolio: Portfolio) -> None:
        rule = DrawdownRiskRule()
        rule._peak_value = 50000.0
        portfolio = empty_portfolio.model_copy(update={"total_value": 100000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.LOW
        assert rule._peak_value == 100000.0


class TestLeverageRiskRule:
    def test_no_leverage(self, empty_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule()
        result = rule.evaluate(empty_portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "Low leverage" in result.messages[0]

    def test_moderate_leverage(self, diversified_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule()
        result = rule.evaluate(diversified_portfolio, {})
        assert result.level == RiskLevel.MEDIUM
        assert "Moderate leverage" in result.messages[0]

    def test_high_leverage(self, empty_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule(warning_threshold=1.5, critical_threshold=2.0)
        portfolio = empty_portfolio.model_copy(update={"cash": 55000.0, "total_value": 100000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.HIGH
        assert "High leverage" in result.messages[0]

    def test_critical_leverage(self, empty_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule(warning_threshold=1.5, critical_threshold=2.0)
        portfolio = empty_portfolio.model_copy(update={"cash": 30000.0, "total_value": 100000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.CRITICAL
        assert "Critical leverage" in result.messages[0]

    def test_negative_cash_with_positions(self, leveraged_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule()
        result = rule.evaluate(leveraged_portfolio, {})
        assert result.level == RiskLevel.CRITICAL
        assert "infinite leverage" in result.messages[0]

    def test_negative_cash_no_positions(self, empty_portfolio: Portfolio) -> None:
        rule = LeverageRiskRule()
        portfolio = empty_portfolio.model_copy(update={"cash": -10000.0, "total_value": -10000.0})
        result = rule.evaluate(portfolio, {})
        assert result.level == RiskLevel.LOW
        assert "No equity" in result.messages[0]


class TestValidationEngineRisk:
    def test_risk_rule_priority(self, concentrated_portfolio: Portfolio) -> None:
        engine = ValidationEngine()
        engine.register_risk_rule(LeverageRiskRule())
        engine.register_risk_rule(ConcentrationRiskRule())

        results = engine.assess_risk(concentrated_portfolio, {})
        assert len(results) == 2
        assert isinstance(results[0], RiskResult)
        assert isinstance(results[1], RiskResult)

    def test_empty_risk_engine(self, empty_portfolio: Portfolio) -> None:
        engine = ValidationEngine()
        results = engine.assess_risk(empty_portfolio, {})
        assert results == []

    def test_combined_risk_assessment(self, leveraged_portfolio: Portfolio) -> None:
        engine = ValidationEngine()
        engine.register_risk_rule(ConcentrationRiskRule())
        engine.register_risk_rule(DrawdownRiskRule())
        engine.register_risk_rule(LeverageRiskRule())

        results = engine.assess_risk(leveraged_portfolio, {})
        assert len(results) == 3
        levels = [r.level for r in results]
        assert RiskLevel.CRITICAL in levels
