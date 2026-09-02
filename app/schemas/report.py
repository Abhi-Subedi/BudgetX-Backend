from pydantic import BaseModel


class CategoryAmount(BaseModel):
    category: str
    amount: float


class BudgetPerformanceItem(BaseModel):
    category: str
    budgeted: float
    spent: float
    remaining: float
    pct_used: float


class GoalProgressItem(BaseModel):
    goal: str
    contributed: float
    target: float
    current: float
    pct_complete: float


class MonthComparison(BaseModel):
    income_change_pct: float
    expense_change_pct: float


class MonthlyReport(BaseModel):
    year: int
    month: int
    total_income: float
    total_expenses: float
    savings: float
    savings_rate: float
    top_categories: list[CategoryAmount]
    budget_performance: list[BudgetPerformanceItem]
    goals_progress: list[GoalProgressItem]
    month_over_month_comparison: MonthComparison
