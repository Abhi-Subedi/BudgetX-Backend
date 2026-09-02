from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Budget, BudgetItem, Category, Transaction, TransactionType
from app.models.enums import CategoryKind
from app.services.common import month_bounds


def get_recommendations(db: Session, user_id: int) -> list[dict]:
    recommendations = []
    today = date.today()
    start, end = month_bounds(f"{today.year}-{today.month:02d}")

    _check_high_spending_categories(db, user_id, start, end, recommendations)
    _check_unused_subscriptions(db, user_id, start, end, recommendations)
    _check_budget_overspending(db, user_id, start, end, recommendations)
    _check_savings_opportunity(db, user_id, start, end, recommendations)

    return recommendations


def _check_high_spending_categories(db: Session, user_id: int, start: date, end: date, recs: list) -> None:
    rows = db.execute(
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
    ).all()
    for category_id, amount in rows:
        if category_id is None:
            continue
        cat = db.get(Category, category_id)
        if cat is None:
            continue
        amt = round(float(amount), 2)
        if cat.name in ("Food & Drink", "Entertainment", "Shopping") and amt > 500:
            recs.append({
                "title": f"High {cat.name} spending",
                "description": f"You've spent ${amt:.2f} on {cat.name} this month. Consider reviewing these expenses.",
                "impact": "high",
                "category": "spending",
            })
        elif amt > 1000:
            recs.append({
                "title": f"High {cat.name} spending",
                "description": f"You've spent ${amt:.2f} on {cat.name} this month. Consider reviewing these expenses.",
                "impact": "medium",
                "category": "spending",
            })


def _check_unused_subscriptions(db: Session, user_id: int, start: date, end: date, recs: list) -> None:
    from app.models.recurring import RecurringTransaction
    from app.models.enums import Frequency
    recurrings = db.scalars(
        select(RecurringTransaction).where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.active.is_(False),
        )
    ).all()
    for r in recurrings:
        recs.append({
            "title": f"Inactive subscription: {r.payee or 'Unknown'}",
            "description": f"Recurring payment of ${float(r.amount):.2f}/{r.frequency.value} is inactive. Consider removing it if no longer needed.",
            "impact": "low",
            "category": "subscriptions",
        })


def _check_budget_overspending(db: Session, user_id: int, start: date, end: date, recs: list) -> None:
    budget = db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.month == start).limit(1))
    if budget is None:
        return
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
        budgeted = round(float(item.amount or 0), 2)
        spent = spent_map.get(item.category_id, 0.0)
        if budgeted > 0 and spent > budgeted:
            cat = db.get(Category, item.category_id)
            cat_name = cat.name if cat else "Unknown"
            overage = round(spent - budgeted, 2)
            recs.append({
                "title": f"Over budget: {cat_name}",
                "description": f"You've exceeded your {cat_name} budget by ${overage:.2f}. Adjust spending for the rest of the month.",
                "impact": "high",
                "category": "budget",
            })


def _check_savings_opportunity(db: Session, user_id: int, start: date, end: date, recs: list) -> None:
    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).one()
    income_f = round(float(income or 0), 2)
    expense_f = round(float(expense or 0), 2)
    if income_f > 0:
        savings_rate = (income_f - expense_f) / income_f * 100
        if savings_rate < 10:
            recs.append({
                "title": "Low savings rate",
                "description": f"Your savings rate is {savings_rate:.1f}%. Aim for at least 20% to build wealth effectively.",
                "impact": "high",
                "category": "savings",
            })
        elif savings_rate < 20:
            recs.append({
                "title": "Room to save more",
                "description": f"Your savings rate is {savings_rate:.1f}%. Increasing to 20%+ could accelerate your financial goals.",
                "impact": "medium",
                "category": "savings",
            })
