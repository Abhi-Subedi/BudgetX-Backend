from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction, TransactionType
from app.services.common import month_bounds, shift_month


def _month_totals(db: Session, user_id: int, start: date, end: date) -> dict:
    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).one()
    income_f = round(float(income), 2)
    expense_f = round(float(expense), 2)
    saved = round(income_f - expense_f, 2)
    return {
        "income": income_f,
        "expense": expense_f,
        "saved": saved,
        "savings_rate": round(saved / income_f * 100, 1) if income_f > 0 else 0.0,
    }


def overview(db: Session, user_id: int, month_key: str) -> dict:
    start, end = month_bounds(month_key)
    prev_start, prev_end = month_bounds(shift_month(month_key, -1))

    totals = _month_totals(db, user_id, start, end)
    prev_totals = _month_totals(db, user_id, prev_start, prev_end)

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
        .order_by(func.sum(Transaction.amount).desc())
    ).all()

    total_expense = sum(float(amount) for _, amount in rows) or 1.0
    by_category = []
    for category_id, amount in rows:
        if category_id is None:
            name, color = "Uncategorized", "#6E685C"
        else:
            cat = db.get(Category, category_id)
            name = cat.name if cat else "Uncategorized"
            color = cat.color if cat else "#6E685C"
        by_category.append(
            {
                "category_id": category_id,
                "name": name,
                "color": color,
                "amount": round(float(amount), 2),
                "pct": round(float(amount) / total_expense * 100, 1),
            }
        )

    largest_rows = db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        .order_by(Transaction.amount.desc())
        .limit(5)
    ).all()

    largest = []
    for t in largest_rows:
        cat_name = None
        if t.category_id is not None:
            cat = db.get(Category, t.category_id)
            cat_name = cat.name if cat else None
        largest.append(
            {
                "id": t.id,
                "payee": t.payee or (cat_name or "Expense"),
                "note": t.note,
                "amount": round(float(t.amount), 2),
                "occurred_at": t.occurred_at.isoformat(),
                "category_name": cat_name,
            }
        )

    return {
        "month": month_key,
        "totals": totals,
        "previous_totals": prev_totals,
        "by_category": by_category,
        "largest_expenses": largest,
    }


_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def trends(db: Session, user_id: int, end_month: str, months: int) -> list[dict]:
    months = max(3, min(months, 24))
    points = []
    cursor_month = end_month
    raw: list[dict] = []
    for _ in range(months):
        start, end = month_bounds(cursor_month)
        totals = _month_totals(db, user_id, start, end)
        year, m = (int(x) for x in cursor_month.split("-"))
        raw.append(
            {
                "month": cursor_month,
                "label": f"{_MONTH_ABBR[m - 1]}",
                "income": totals["income"],
                "expense": totals["expense"],
            }
        )
        cursor_month = shift_month(cursor_month, -1)
    return list(reversed(raw))
