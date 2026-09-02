from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Budget, BudgetItem, Category, SavingsGoal, Transaction, TransactionType
from app.models.enums import CategoryKind
from app.services.common import month_bounds, shift_month


def generate_monthly_report(db: Session, user_id: int, year: int, month: int) -> dict:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).one()
    income_f = round(float(income or 0), 2)
    expense_f = round(float(expense or 0), 2)
    saved = round(income_f - expense_f, 2)
    savings_rate = round(saved / income_f * 100, 1) if income_f > 0 else 0.0

    cat_rows = db.execute(
        select(
            Transaction.category_id,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        .group_by(Transaction.category_id)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()
    top_categories = []
    for category_id, amount in cat_rows:
        if category_id is None:
            name = "Uncategorized"
        else:
            cat = db.get(Category, category_id)
            name = cat.name if cat else "Uncategorized"
        top_categories.append({"category": name, "amount": round(float(amount), 2)})

    budget = db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.month == start).limit(1))
    budget_performance = []
    if budget is not None:
        spent_map: dict[int, float] = {}
        rows = db.execute(
            select(Transaction.category_id, func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.expense,
                Transaction.occurred_at >= start,
                Transaction.occurred_at < end,
            )
            .group_by(Transaction.category_id)
        ).all()
        for cid, total in rows:
            spent_map[cid] = round(float(total), 2)

        items = db.scalars(select(BudgetItem).where(BudgetItem.budget_id == budget.id)).all()
        for item in items:
            cat = db.get(Category, item.category_id)
            cat_name = cat.name if cat else "Unknown"
            budgeted = round(float(item.amount or 0), 2)
            spent = spent_map.get(item.category_id, 0.0)
            remaining = round(budgeted - spent, 2)
            pct_used = round(spent / budgeted * 100, 1) if budgeted > 0 else 100.0
            budget_performance.append({
                "category": cat_name,
                "budgeted": budgeted,
                "spent": spent,
                "remaining": remaining,
                "pct_used": min(pct_used, 999),
            })

    goals = db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user_id)).all()
    goals_progress = []
    for goal in goals:
        target = round(float(goal.target_amount), 2)
        current = round(float(goal.current_amount), 2)
        pct_complete = round(current / target * 100, 1) if target > 0 else 0.0
        goals_progress.append({
            "goal": goal.name,
            "contributed": 0.0,
            "target": target,
            "current": current,
            "pct_complete": min(pct_complete, 100.0),
        })

    prev_month_key = shift_month(f"{year}-{month:02d}", -1)
    prev_start, prev_end = month_bounds(prev_month_key)
    prev_income, prev_expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= prev_start, Transaction.occurred_at < prev_end)
    ).one()
    prev_income_f = round(float(prev_income or 0), 2)
    prev_expense_f = round(float(prev_expense or 0), 2)
    income_change = round((income_f - prev_income_f) / prev_income_f * 100, 1) if prev_income_f > 0 else 0.0
    expense_change = round((expense_f - prev_expense_f) / prev_expense_f * 100, 1) if prev_expense_f > 0 else 0.0

    return {
        "year": year,
        "month": month,
        "total_income": income_f,
        "total_expenses": expense_f,
        "savings": saved,
        "savings_rate": savings_rate,
        "top_categories": top_categories,
        "budget_performance": budget_performance,
        "goals_progress": goals_progress,
        "month_over_month_comparison": {
            "income_change_pct": income_change,
            "expense_change_pct": expense_change,
        },
    }
