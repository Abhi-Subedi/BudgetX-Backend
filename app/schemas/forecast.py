from datetime import date

from pydantic import BaseModel, field_validator


def _round2(v: float) -> float:
    return round(float(v), 2)


class BalanceProjection(BaseModel):
    current_balance: float
    avg_daily_income: float
    avg_daily_expense: float
    days_ahead: int
    projected_balance: float

    @field_validator("current_balance", "avg_daily_income", "avg_daily_expense", "projected_balance")
    @classmethod
    def round_amounts(cls, v) -> float:
        return _round2(float(v))


class SpendingSlice(BaseModel):
    category_id: int | None
    category_name: str
    avg_monthly_amount: float
    projected_amount: float

    @field_validator("avg_monthly_amount", "projected_amount")
    @classmethod
    def round_amounts(cls, v) -> float:
        return _round2(float(v))


class SpendingProjection(BaseModel):
    months_ahead: int
    total_avg_monthly: float
    total_projected: float
    by_category: list[SpendingSlice]

    @field_validator("total_avg_monthly", "total_projected")
    @classmethod
    def round_amounts(cls, v) -> float:
        return _round2(float(v))


class CashShortageWarning(BaseModel):
    has_warning: bool
    days_until_shortage: int | None
    shortage_date: date | None
    projected_balance: float
    threshold: float

    @field_validator("projected_balance", "threshold")
    @classmethod
    def round_amounts(cls, v) -> float:
        return _round2(float(v))


class GoalFeasibility(BaseModel):
    goal_id: int
    goal_name: str
    target_amount: float
    current_amount: float
    remaining: float
    deadline: date | None
    monthly_contribution: float
    months_needed: float | None
    feasible: bool
    shortfall: float | None

    @field_validator(
        "target_amount", "current_amount", "remaining",
        "monthly_contribution", "months_needed", "shortfall",
    )
    @classmethod
    def round_amounts(cls, v) -> float | None:
        return _round2(float(v)) if v is not None else None
