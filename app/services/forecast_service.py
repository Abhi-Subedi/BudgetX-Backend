from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Category, SavingsGoal, Transaction, TransactionType
from app.schemas.forecast import (
    BalanceProjection,
    CashShortageWarning,
    GoalFeasibility,
    SpendingProjection,
    SpendingSlice,
)


def _daily_averages(db: Session, user_id: int, days: int = 90) -> tuple[float, float]:
    start = date.today() - timedelta(days=days)
    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start)
    ).one()
    income_f = float(income)
    expense_f = float(expense)
    avg_income = round(income_f / days, 2) if days > 0 else 0.0
    avg_expense = round(expense_f / days, 2) if days > 0 else 0.0
    return avg_income, avg_expense


def _current_balance(db: Session, user_id: int) -> float:
    from app.services.common import total_balance

    return total_balance(db, user_id)


def project_balance(db: Session, user_id: int, days_ahead: int = 30) -> BalanceProjection:
    avg_income, avg_expense = _daily_averages(db, user_id)
    current = _current_balance(db, user_id)
    net_daily = avg_income - avg_expense
    projected = round(current + net_daily * days_ahead, 2)
    return BalanceProjection(
        current_balance=current,
        avg_daily_income=avg_income,
        avg_daily_expense=avg_expense,
        days_ahead=days_ahead,
        projected_balance=projected,
    )


def project_spending(db: Session, user_id: int, months_ahead: int = 3) -> SpendingProjection:
    months_ahead = max(1, min(months_ahead, 24))
    months_to_sample = 3
    start = date.today() - timedelta(days=months_to_sample * 31)

    rows = db.execute(
        select(
            Transaction.category_id,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.occurred_at >= start,
        )
        .group_by(Transaction.category_id)
    ).all()

    by_category: list[SpendingSlice] = []
    total_avg = 0.0
    total_projected = 0.0

    for category_id, amount in rows:
        amount_f = float(amount)
        avg_monthly = round(amount_f / months_to_sample, 2) if months_to_sample > 0 else 0.0
        projected = round(avg_monthly * months_ahead, 2)

        if category_id is None:
            cat_name = "Uncategorized"
        else:
            cat = db.get(Category, category_id)
            cat_name = cat.name if cat else "Uncategorized"

        by_category.append(
            SpendingSlice(
                category_id=category_id,
                category_name=cat_name,
                avg_monthly_amount=avg_monthly,
                projected_amount=projected,
            )
        )
        total_avg += avg_monthly
        total_projected += projected

    by_category.sort(key=lambda s: s.projected_amount, reverse=True)

    return SpendingProjection(
        months_ahead=months_ahead,
        total_avg_monthly=round(total_avg, 2),
        total_projected=round(total_projected, 2),
        by_category=by_category,
    )


def get_cash_shortage_warning(db: Session, user_id: int, threshold: float = 100.0) -> CashShortageWarning:
    avg_income, avg_expense = _daily_averages(db, user_id)
    current = _current_balance(db, user_id)
    net_daily = avg_income - avg_expense

    if net_daily >= 0:
        return CashShortageWarning(
            has_warning=False,
            days_until_shortage=None,
            shortage_date=None,
            projected_balance=current,
            threshold=threshold,
        )

    if current <= threshold:
        return CashShortageWarning(
            has_warning=True,
            days_until_shortage=0,
            shortage_date=date.today(),
            projected_balance=current,
            threshold=threshold,
        )

    days_until = int(current / abs(net_daily))
    shortage_date = date.today() + timedelta(days=days_until)

    return CashShortageWarning(
        has_warning=True,
        days_until_shortage=days_until,
        shortage_date=shortage_date,
        projected_balance=current,
        threshold=threshold,
    )


def get_goal_feasibility(
    db: Session, user_id: int, goal_id: int, monthly_contribution: float
) -> GoalFeasibility:
    goal = db.get(SavingsGoal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise AppError(404, "Goal not found.")

    target = float(goal.target_amount)
    current = float(goal.current_amount or 0)
    remaining = max(0.0, target - current)

    feasible = True
    months_needed: float | None = None
    shortfall: float | None = None

    if monthly_contribution > 0:
        months_needed = round(remaining / monthly_contribution, 1) if remaining > 0 else 0.0
        if goal.deadline is not None:
            today = date.today()
            days_left = (goal.deadline - today).days
            months_available = round(days_left / 30.44, 1) if days_left > 0 else 0.0
            if months_needed > months_available:
                feasible = False
                shortfall = round(target - (current + monthly_contribution * months_available), 2)
    else:
        if remaining > 0:
            feasible = False

    return GoalFeasibility(
        goal_id=goal.id,
        goal_name=goal.name,
        target_amount=target,
        current_amount=current,
        remaining=remaining,
        deadline=goal.deadline,
        monthly_contribution=monthly_contribution,
        months_needed=months_needed,
        feasible=feasible,
        shortfall=shortfall,
    )
