from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LoanType(Enum):
    MARGIN = "margin"
    SHORT = "short"


class LoanStatus(Enum):
    ACTIVE = "active"
    REPAID = "repaid"
    LIQUIDATED = "liquidated"
    DEFAULTED = "defaulted"


class Loan(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(..., description="Unique loan identifier")
    agent_id: str = Field(..., description="Agent who borrowed")
    type: LoanType = Field(..., description="Loan type")
    principal: float = Field(..., gt=0, description="Borrowed principal amount")
    interest_rate: float = Field(..., ge=0, description="Daily interest rate")
    borrowed_at: datetime = Field(default_factory=datetime.utcnow, description="Loan creation timestamp")
    due_at: datetime = Field(..., description="Loan due timestamp")
    status: LoanStatus = Field(default=LoanStatus.ACTIVE, description="Current loan status")
    collateral_value: float = Field(default=0.0, ge=0, description="Value of collateral posted")
    current_debt: float = Field(..., gt=0, description="Current outstanding debt including interest")

    def model_post_init(self, __context: object) -> None:
        if self.current_debt <= 0:
            object.__setattr__(self, "current_debt", self.principal)


class MarginAccount(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str = Field(..., description="Agent identifier")
    equity: float = Field(..., description="Account equity (total value - debt)")
    margin_used: float = Field(..., ge=0, description="Total margin used")
    buying_power: float = Field(..., description="Available buying power")
    margin_call_level: float = Field(..., description="Equity ratio triggering margin call")
    liquidation_level: float = Field(..., description="Equity ratio triggering forced liquidation")
