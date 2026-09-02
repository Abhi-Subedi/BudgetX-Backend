from pydantic import BaseModel, Field, field_validator

from app.schemas.goal import GoalOut
from app.schemas.transaction import TransactionOut


class MonthTotals(BaseModel):
    income: float
    expense: float
    saved: float
    savings_rate: float


class SpendingPoint(BaseModel):
    day: int
    current: float
    previous: float


class BudgetAttention(BaseModel):
    budget_id: int
    item_id: int
    category_name: str
    pct_used: float


class UpcomingRecurring(BaseModel):
    id: int
    payee: str | None
    amount: float
    next_run_date: object
    frequency: str


class DashboardOut(BaseModel):
    balance_total: float
    month: MonthTotals
    previous_month: MonthTotals
    spending_series: list[SpendingPoint]
    budgets: list[BudgetAttention]
    recent_transactions: list[TransactionOut]
    goals: list[GoalOut]
    upcoming_recurring: list[UpcomingRecurring]
