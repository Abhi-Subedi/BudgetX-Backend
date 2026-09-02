from datetime import date

from pydantic import BaseModel


class CategorySlice(BaseModel):
    category_id: int | None
    name: str
    color: str
    amount: float
    pct: float


class LargestExpense(BaseModel):
    id: int
    payee: str | None
    note: str | None
    amount: float
    occurred_at: date
    category_name: str | None


class AnalyticsOverview(BaseModel):
    month: str
    totals: "MonthSummary"
    previous_totals: "MonthSummary"
    by_category: list[CategorySlice]
    largest_expenses: list[LargestExpense]


class MonthSummary(BaseModel):
    income: float
    expense: float
    saved: float
    savings_rate: float


class TrendPoint(BaseModel):
    month: str
    label: str
    income: float
    expense: float
