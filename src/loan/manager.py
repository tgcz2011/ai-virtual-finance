from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.engine.order.models import Order, OrderSide, OrderType, Trade
from src.engine.portfolio.models import Portfolio
from src.loan.models import Loan, LoanStatus, LoanType, MarginAccount

if TYPE_CHECKING:
    from src.engine.order.order_book import OrderBook


class LoanManager:
    """Manages margin and short loans for agents."""

    def __init__(
        self,
        initial_margin_requirement: float = 0.5,
        maintenance_margin: float = 0.25,
        daily_interest_rate: float = 0.0005,
        default_loan_days: int = 30,
    ) -> None:
        self._initial_margin_requirement = initial_margin_requirement
        self._maintenance_margin = maintenance_margin
        self._daily_interest_rate = daily_interest_rate
        self._default_loan_days = default_loan_days
        self._loans: dict[str, Loan] = {}
        self._agent_loans: dict[str, list[str]] = {}
        self._margin_used: dict[str, float] = {}
        self._short_positions: dict[str, dict[str, float]] = {}

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _total_margin_debt(self, agent_id: str) -> float:
        return sum(
            loan.current_debt
            for loan in self._agent_active_loans(agent_id)
            if loan.type == LoanType.MARGIN
        )

    def _total_short_debt(self, agent_id: str) -> float:
        return sum(
            loan.current_debt
            for loan in self._agent_active_loans(agent_id)
            if loan.type == LoanType.SHORT
        )

    def _agent_active_loans(self, agent_id: str) -> list[Loan]:
        loan_ids = self._agent_loans.get(agent_id, [])
        return [
            self._loans[loan_id]
            for loan_id in loan_ids
            if self._loans[loan_id].status == LoanStatus.ACTIVE
        ]

    def _equity_ratio(self, agent_id: str, portfolio: Portfolio) -> float:
        total_debt = self._total_margin_debt(agent_id) + self._total_short_debt(agent_id)
        if portfolio.total_value <= 0:
            return 0.0
        equity = portfolio.total_value - total_debt
        return equity / portfolio.total_value

    def request_margin_loan(
        self,
        agent_id: str,
        amount: float,
        portfolio: Portfolio,
    ) -> Loan | None:
        """Request a margin loan backed by the agent's portfolio."""
        if amount <= 0:
            return None
        if agent_id != portfolio.agent_id:
            return None

        total_debt = self._total_margin_debt(agent_id) + self._total_short_debt(agent_id)
        equity = portfolio.total_value - total_debt

        max_loan = equity * (1 - self._initial_margin_requirement) / self._initial_margin_requirement
        if max_loan <= 0 or amount > max_loan:
            return None

        now = self._now()
        due = now + timedelta(days=self._default_loan_days)
        loan = Loan(
            id=self._generate_id(),
            agent_id=agent_id,
            type=LoanType.MARGIN,
            principal=amount,
            interest_rate=self._daily_interest_rate,
            borrowed_at=now,
            due_at=due,
            status=LoanStatus.ACTIVE,
            collateral_value=portfolio.total_value,
            current_debt=amount,
        )

        self._loans[loan.id] = loan
        self._agent_loans.setdefault(agent_id, []).append(loan.id)
        self._margin_used[agent_id] = self._margin_used.get(agent_id, 0.0) + amount

        return loan

    def request_short_loan(
        self,
        agent_id: str,
        symbol: str,
        quantity: float,
        portfolio: Portfolio,
    ) -> Loan | None:
        """Request a short-selling loan (borrow shares to sell short)."""
        if quantity <= 0 or not symbol:
            return None
        if agent_id != portfolio.agent_id:
            return None

        # Need current price from portfolio position or assume we have a price
        position = portfolio.positions.get(symbol)
        if position is None:
            return None
        price = position.current_price
        if price <= 0:
            return None

        amount = quantity * price
        total_debt = self._total_margin_debt(agent_id) + self._total_short_debt(agent_id)
        equity = portfolio.total_value - total_debt

        max_loan = equity * (1 - self._initial_margin_requirement) / self._initial_margin_requirement
        if max_loan <= 0 or amount > max_loan:
            return None

        now = self._now()
        due = now + timedelta(days=self._default_loan_days)
        loan = Loan(
            id=self._generate_id(),
            agent_id=agent_id,
            type=LoanType.SHORT,
            principal=amount,
            interest_rate=self._daily_interest_rate,
            borrowed_at=now,
            due_at=due,
            status=LoanStatus.ACTIVE,
            collateral_value=portfolio.total_value,
            current_debt=amount,
        )

        self._loans[loan.id] = loan
        self._agent_loans.setdefault(agent_id, []).append(loan.id)
        short_positions = self._short_positions.setdefault(agent_id, {})
        short_positions[symbol] = short_positions.get(symbol, 0.0) + quantity

        return loan

    def repay_loan(
        self,
        loan_id: str,
        amount: float,
        portfolio: Portfolio,
    ) -> bool:
        """Repay part or all of a loan. Returns True if repayment succeeds."""
        if amount <= 0:
            return False
        loan = self._loans.get(loan_id)
        if loan is None or loan.status != LoanStatus.ACTIVE:
            return False
        if loan.agent_id != portfolio.agent_id:
            return False
        if portfolio.cash < amount:
            return False

        repay = min(amount, loan.current_debt)
        loan.current_debt -= repay
        if loan.current_debt <= 0:
            loan.current_debt = 0.0
            loan.status = LoanStatus.REPAID

        if loan.type == LoanType.MARGIN:
            self._margin_used[loan.agent_id] = max(
                0.0,
                self._margin_used.get(loan.agent_id, 0.0) - repay,
            )
        elif loan.type == LoanType.SHORT and loan.status == LoanStatus.REPAID:
            # We don't track per-loan short quantity precisely; clear symbol if no other short loans
            remaining_short_debt = self._total_short_debt(loan.agent_id)
            if remaining_short_debt <= 0:
                self._short_positions[loan.agent_id] = {}

        return True

    def check_margin_call(self, agent_id: str, portfolio: Portfolio) -> bool:
        """Check if the agent's account is in margin call territory."""
        if agent_id != portfolio.agent_id:
            return False
        ratio = self._equity_ratio(agent_id, portfolio)
        return ratio <= self._maintenance_margin and ratio > 0

    def liquidate(
        self,
        agent_id: str,
        portfolio: Portfolio,
        order_book: OrderBook,
    ) -> list[Trade]:
        """Force-liquidate agent positions to cover debt. Returns list of trades."""
        if agent_id != portfolio.agent_id:
            return []

        total_debt = self._total_margin_debt(agent_id) + self._total_short_debt(agent_id)
        if total_debt <= 0:
            return []

        trades: list[Trade] = []
        cash_raised = 0.0

        # Liquidate long positions first
        for symbol, position in list(portfolio.positions.items()):
            if position.quantity <= 0:
                continue
            order = Order(
                id=self._generate_id(),
                agent_id=agent_id,
                symbol=symbol,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                quantity=float(position.quantity),
                price=None,
            )
            order_trades = order_book.add_order(order)
            trades.extend(order_trades)
            for trade in order_trades:
                cash_raised += trade.quantity * trade.price

        # Cover short positions by buying back
        short_positions = self._short_positions.get(agent_id, {})
        for symbol, qty in list(short_positions.items()):
            if qty <= 0:
                continue
            order = Order(
                id=self._generate_id(),
                agent_id=agent_id,
                symbol=symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=qty,
                price=None,
            )
            order_trades = order_book.add_order(order)
            trades.extend(order_trades)
            for trade in order_trades:
                cash_raised -= trade.quantity * trade.price

        # Mark loans as liquidated/defaulted based on coverage
        for loan in self._agent_active_loans(agent_id):
            if cash_raised >= loan.current_debt:
                cash_raised -= loan.current_debt
                loan.status = LoanStatus.LIQUIDATED
                loan.current_debt = 0.0
            else:
                loan.current_debt -= cash_raised
                cash_raised = 0.0
                loan.status = LoanStatus.DEFAULTED

        self._margin_used[agent_id] = 0.0
        self._short_positions[agent_id] = {}

        return trades

    def get_margin_account(self, agent_id: str, portfolio: Portfolio) -> MarginAccount:
        """Get the margin account summary for an agent."""
        total_debt = self._total_margin_debt(agent_id) + self._total_short_debt(agent_id)
        equity = portfolio.total_value - total_debt
        buying_power = max(0.0, equity * (1 / self._initial_margin_requirement - 1))
        margin_used = self._margin_used.get(agent_id, 0.0)

        return MarginAccount(
            agent_id=agent_id,
            equity=equity,
            margin_used=margin_used,
            buying_power=buying_power,
            margin_call_level=self._maintenance_margin,
            liquidation_level=self._maintenance_margin * 0.5,
        )

    def calculate_interest(self, loan: Loan, days: int) -> float:
        """Calculate simple interest accrued on a loan over a number of days."""
        if days <= 0:
            return 0.0
        return loan.principal * loan.interest_rate * days
