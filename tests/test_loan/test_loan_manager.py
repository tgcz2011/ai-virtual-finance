from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.engine.order.models import Order, OrderSide, OrderStatus, OrderType
from src.engine.order.order_book import OrderBook
from src.engine.portfolio.models import Portfolio, Position
from src.loan.manager import LoanManager
from src.loan.models import Loan, LoanStatus, LoanType, MarginAccount


AGENT_ID = "agent-001"


def _make_portfolio(
    cash: float = 10000.0,
    positions: dict[str, Position] | None = None,
    total_value: float | None = None,
) -> Portfolio:
    if positions is None:
        positions = {
            "AAPL": Position(
                symbol="AAPL",
                quantity=100,
                average_cost=100.0,
                current_price=150.0,
                unrealized_pnl=5000.0,
                realized_pnl=0.0,
                market_value=15000.0,
            ),
        }
    computed_total = cash + sum(p.market_value for p in positions.values())
    return Portfolio(
        agent_id=AGENT_ID,
        cash=cash,
        positions=positions,
        total_value=total_value if total_value is not None else computed_total,
        total_pnl=0.0,
    )


@pytest.fixture
def manager() -> LoanManager:
    return LoanManager(
        initial_margin_requirement=0.5,
        maintenance_margin=0.25,
        daily_interest_rate=0.0005,
        default_loan_days=30,
    )


@pytest.fixture
def portfolio() -> Portfolio:
    return _make_portfolio()


class TestMarginLoan:
    def test_request_margin_loan_success(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 5000.0, portfolio)
        assert loan is not None
        assert loan.type == LoanType.MARGIN
        assert loan.principal == 5000.0
        assert loan.status == LoanStatus.ACTIVE
        assert loan.current_debt == 5000.0

    def test_request_margin_loan_invalid_amount(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_margin_loan(AGENT_ID, 0.0, portfolio) is None
        assert manager.request_margin_loan(AGENT_ID, -100.0, portfolio) is None

    def test_request_margin_loan_exceeds_max(self, manager: LoanManager, portfolio: Portfolio) -> None:
        # portfolio total_value = 25000, equity = 25000, max_loan = 25000
        assert manager.request_margin_loan(AGENT_ID, 30000.0, portfolio) is None

    def test_request_margin_loan_wrong_agent(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_margin_loan("other-agent", 1000.0, portfolio) is None

    def test_request_margin_loan_zero_equity(self, manager: LoanManager) -> None:
        empty_portfolio = _make_portfolio(cash=0.0, positions={})
        assert manager.request_margin_loan(AGENT_ID, 100.0, empty_portfolio) is None


class TestShortLoan:
    def test_request_short_loan_success(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_short_loan(AGENT_ID, "AAPL", 10.0, portfolio)
        assert loan is not None
        assert loan.type == LoanType.SHORT
        assert loan.principal == 10.0 * 150.0
        assert loan.status == LoanStatus.ACTIVE

    def test_request_short_loan_invalid_quantity(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_short_loan(AGENT_ID, "AAPL", 0.0, portfolio) is None
        assert manager.request_short_loan(AGENT_ID, "AAPL", -5.0, portfolio) is None

    def test_request_short_loan_unknown_symbol(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_short_loan(AGENT_ID, "UNKNOWN", 10.0, portfolio) is None

    def test_request_short_loan_wrong_agent(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_short_loan("other-agent", "AAPL", 10.0, portfolio) is None

    def test_request_short_loan_exceeds_max(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.request_short_loan(AGENT_ID, "AAPL", 200.0, portfolio) is None


class TestRepayLoan:
    def test_repay_margin_loan_full(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        result = manager.repay_loan(loan.id, 2000.0, cash_portfolio)
        assert result is True
        assert loan.status == LoanStatus.REPAID
        assert loan.current_debt == 0.0

    def test_repay_margin_loan_partial(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        result = manager.repay_loan(loan.id, 1000.0, cash_portfolio)
        assert result is True
        assert loan.status == LoanStatus.ACTIVE
        assert loan.current_debt == 1000.0

    def test_repay_insufficient_cash(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan is not None
        poor_portfolio = _make_portfolio(cash=100.0, positions=portfolio.positions)
        result = manager.repay_loan(loan.id, 500.0, poor_portfolio)
        assert result is False

    def test_repay_nonexistent_loan(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.repay_loan("no-such-id", 100.0, portfolio) is False

    def test_repay_already_repaid(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        manager.repay_loan(loan.id, 2000.0, cash_portfolio)
        assert manager.repay_loan(loan.id, 100.0, cash_portfolio) is False

    def test_repay_wrong_agent(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan is not None
        other_portfolio = Portfolio(
            agent_id="other-agent",
            cash=5000.0,
            positions={},
            total_value=5000.0,
            total_pnl=0.0,
        )
        assert manager.repay_loan(loan.id, 100.0, other_portfolio) is False

    def test_repay_short_loan(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_short_loan(AGENT_ID, "AAPL", 10.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        result = manager.repay_loan(loan.id, loan.current_debt, cash_portfolio)
        assert result is True
        assert loan.status == LoanStatus.REPAID


class TestMarginCall:
    def test_no_margin_call_healthy(self, manager: LoanManager, portfolio: Portfolio) -> None:
        manager.request_margin_loan(AGENT_ID, 5000.0, portfolio)
        assert manager.check_margin_call(AGENT_ID, portfolio) is False

    def test_margin_call_triggered(self, manager: LoanManager) -> None:
        # Small portfolio with large loan -> low equity ratio
        small_portfolio = _make_portfolio(
            cash=1000.0,
            positions={
                "AAPL": Position(
                    symbol="AAPL",
                    quantity=10,
                    average_cost=100.0,
                    current_price=100.0,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    market_value=1000.0,
                ),
            },
        )
        manager.request_margin_loan(AGENT_ID, 1500.0, small_portfolio)
        # total_value = 2000, debt = 1500, equity = 500, ratio = 0.25
        # maintenance_margin = 0.25, ratio < maintenance_margin -> margin call
        assert manager.check_margin_call(AGENT_ID, small_portfolio) is True

    def test_margin_call_wrong_agent(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.check_margin_call("other-agent", portfolio) is False

    def test_margin_call_no_debt(self, manager: LoanManager, portfolio: Portfolio) -> None:
        assert manager.check_margin_call(AGENT_ID, portfolio) is False


class TestLiquidation:
    def test_liquidate_no_debt(self, manager: LoanManager, portfolio: Portfolio) -> None:
        order_book = OrderBook()
        trades = manager.liquidate(AGENT_ID, portfolio, order_book)
        assert trades == []

    def test_liquidate_covers_debt(self, manager: LoanManager) -> None:
        # Create an order book with a buyer so liquidation can match
        order_book = OrderBook()
        buy_order = Order(
            id="buy-1",
            agent_id="buyer",
            symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=100.0,
            price=150.0,
        )
        order_book.add_order(buy_order)

        portfolio = _make_portfolio()
        loan = manager.request_margin_loan(AGENT_ID, 5000.0, portfolio)
        assert loan is not None

        trades = manager.liquidate(AGENT_ID, portfolio, order_book)
        assert len(trades) > 0
        assert loan.status in (LoanStatus.LIQUIDATED, LoanStatus.DEFAULTED)

    def test_liquidate_wrong_agent(self, manager: LoanManager, portfolio: Portfolio) -> None:
        order_book = OrderBook()
        assert manager.liquidate("other-agent", portfolio, order_book) == []

    def test_liquidate_short_position(self, manager: LoanManager) -> None:
        order_book = OrderBook()
        # Add a sell order so buy-back can match
        sell_order = Order(
            id="sell-1",
            agent_id="seller",
            symbol="AAPL",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=10.0,
            price=150.0,
        )
        order_book.add_order(sell_order)

        portfolio = _make_portfolio()
        loan = manager.request_short_loan(AGENT_ID, "AAPL", 10.0, portfolio)
        assert loan is not None

        trades = manager.liquidate(AGENT_ID, portfolio, order_book)
        # May or may not produce trades depending on matching, but should not error
        assert isinstance(trades, list)
        assert loan.status in (LoanStatus.LIQUIDATED, LoanStatus.DEFAULTED)


class TestInterestCalculation:
    def test_calculate_interest_positive_days(self, manager: LoanManager) -> None:
        loan = Loan(
            id="loan-1",
            agent_id=AGENT_ID,
            type=LoanType.MARGIN,
            principal=10000.0,
            interest_rate=0.0005,
            borrowed_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=30),
            current_debt=10000.0,
        )
        interest = manager.calculate_interest(loan, 10)
        assert interest == pytest.approx(10000.0 * 0.0005 * 10)

    def test_calculate_interest_zero_days(self, manager: LoanManager) -> None:
        loan = Loan(
            id="loan-1",
            agent_id=AGENT_ID,
            type=LoanType.MARGIN,
            principal=10000.0,
            interest_rate=0.0005,
            borrowed_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=30),
            current_debt=10000.0,
        )
        assert manager.calculate_interest(loan, 0) == 0.0

    def test_calculate_interest_negative_days(self, manager: LoanManager) -> None:
        loan = Loan(
            id="loan-1",
            agent_id=AGENT_ID,
            type=LoanType.MARGIN,
            principal=10000.0,
            interest_rate=0.0005,
            borrowed_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=30),
            current_debt=10000.0,
        )
        assert manager.calculate_interest(loan, -5) == 0.0


class TestMarginAccount:
    def test_get_margin_account(self, manager: LoanManager, portfolio: Portfolio) -> None:
        manager.request_margin_loan(AGENT_ID, 5000.0, portfolio)
        account = manager.get_margin_account(AGENT_ID, portfolio)
        assert isinstance(account, MarginAccount)
        assert account.agent_id == AGENT_ID
        assert account.margin_used == 5000.0
        assert account.margin_call_level == 0.25
        assert account.liquidation_level == 0.125

    def test_get_margin_account_no_loans(self, manager: LoanManager, portfolio: Portfolio) -> None:
        account = manager.get_margin_account(AGENT_ID, portfolio)
        assert account.equity == portfolio.total_value
        assert account.margin_used == 0.0
        assert account.buying_power == pytest.approx(portfolio.total_value * (1 / 0.5 - 1))

    def test_get_margin_account_with_short(self, manager: LoanManager, portfolio: Portfolio) -> None:
        manager.request_short_loan(AGENT_ID, "AAPL", 10.0, portfolio)
        account = manager.get_margin_account(AGENT_ID, portfolio)
        assert account.margin_used == 0.0  # short loans don't count as margin_used
        assert account.equity == portfolio.total_value - 1500.0


class TestEdgeCases:
    def test_multiple_margin_loans(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan1 = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        loan2 = manager.request_margin_loan(AGENT_ID, 2000.0, portfolio)
        assert loan1 is not None
        assert loan2 is not None
        assert manager.get_margin_account(AGENT_ID, portfolio).margin_used == 4000.0

    def test_margin_used_decreases_on_repay(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 3000.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        manager.repay_loan(loan.id, 1000.0, cash_portfolio)
        assert manager.get_margin_account(AGENT_ID, cash_portfolio).margin_used == 2000.0

    def test_loan_status_after_full_repay(self, manager: LoanManager, portfolio: Portfolio) -> None:
        loan = manager.request_margin_loan(AGENT_ID, 1000.0, portfolio)
        assert loan is not None
        cash_portfolio = _make_portfolio(cash=5000.0, positions=portfolio.positions)
        manager.repay_loan(loan.id, 1000.0, cash_portfolio)
        assert loan.status == LoanStatus.REPAID

    def test_liquidation_level(self, manager: LoanManager) -> None:
        account = manager.get_margin_account(AGENT_ID, _make_portfolio())
        assert account.liquidation_level == account.margin_call_level * 0.5
