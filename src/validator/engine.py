from __future__ import annotations

from src.engine.order.models import Order
from src.engine.portfolio.models import Portfolio
from src.validator.rules.order_rules import OrderValidationRule, ValidationResult
from src.validator.rules.risk_rules import RiskResult, RiskRule


class ValidationEngine:
    """Engine that orchestrates order validation and risk assessment rules."""

    def __init__(self) -> None:
        self._order_rules: list[OrderValidationRule] = []
        self._risk_rules: list[RiskRule] = []
        self._short_circuit: bool = True

    def set_short_circuit(self, enabled: bool) -> None:
        """Enable or disable short-circuit logic for order validation."""
        self._short_circuit = enabled

    def register_order_rule(self, rule: OrderValidationRule) -> None:
        """Register an order validation rule."""
        self._order_rules.append(rule)
        self._order_rules.sort(key=lambda r: r.priority)

    def register_risk_rule(self, rule: RiskRule) -> None:
        """Register a risk evaluation rule."""
        self._risk_rules.append(rule)
        self._risk_rules.sort(key=lambda r: r.priority)

    def validate_order(self, order: Order, portfolio: Portfolio) -> ValidationResult:
        """Validate an order against all registered order rules."""
        all_errors: list[str] = []

        for rule in self._order_rules:
            result = rule.validate(order, portfolio)
            if not result.valid:
                all_errors.extend(result.errors)
                if self._short_circuit:
                    return ValidationResult(valid=False, errors=all_errors)

        if all_errors:
            return ValidationResult(valid=False, errors=all_errors)

        return ValidationResult(valid=True)

    def assess_risk(
        self, portfolio: Portfolio, market_data: dict[str, float]
    ) -> list[RiskResult]:
        """Assess portfolio risk using all registered risk rules."""
        results: list[RiskResult] = []

        for rule in self._risk_rules:
            result = rule.evaluate(portfolio, market_data)
            results.append(result)

        return results
