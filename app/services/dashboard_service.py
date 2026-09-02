from datetime import date, timedelta

from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.models import Budget, RecurringTransaction, SavingsGoal, Transaction, TransactionType
from app.services import recurring_service
from app.services.budget_service import progress_for
from app.services.common import month_bounds, shift_month, total_balance
from app.services.serializers import transactions_to_list


def _totals(db: Session, user_id: int, start: date, end: date) -> dict:
    income, expense = db.execute(
        select(
            func.coalesce(
                func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0
            ),
            func.coalesce(
                func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0
            ),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).one()
    income_f = round(float(income or 0), 2)
    expense_f = round(float(expense or 0), 2)
    saved = round(income_f - expense_f, 2)
    rate = round(saved / income_f * 100, 1) if income_f > 0 else 0.0
    return {"income": income_f, "expense": expense_f, "saved": saved, "savings_rate": rate}


def _daily_expenses(db: Session, user_id: int, start: date, end: date) -> dict[int, float]:
    rows = db.execute(
        select(extract("day", Transaction.occurred_at), func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        .group_by(extract("day", Transaction.occurred_at))
    ).all()
    daily: dict[int, float] = {}
    for day_val, amount in rows:
        try:
            daily[int(day_val)] = float(amount or 0)
        except (TypeError, ValueError):
            continue
    return daily


def _spending_series(db: Session, user_id: int, month_key: str) -> list[dict]:
    start, end = month_bounds(month_key)
    prev_start, prev_end = month_bounds(shift_month(month_key, -1))
    days_in_month = (end - start).days
    prev_days = (prev_end - prev_start).days

    daily_current = _daily_expenses(db, user_id, start, end)
    daily_prev = _daily_expenses(db, user_id, prev_start, prev_end)

    series = []
    cum_c = cum_p = 0.0
    for d in range(1, days_in_month + 1):
        cum_c += daily_current.get(d, 0.0)
        if d <= min(days_in_month, prev_days):
            cum_p += daily_prev.get(d, 0.0)
        series.append({"day": d, "current": round(cum_c, 2), "previous": round(cum_p, 2)})
    return series


def build_dashboard(db: Session, user) -> dict:
    today_ = date.today()
    month_key = f"{today_.year}-{today_.month:02d}"
    start, end = month_bounds(month_key)

    recurring_service.materialize_due(db, user.id)

    balance = total_balance(db, user.id)
    totals = _totals(db, user.id, start, end)
    prev_start, prev_end = month_bounds(shift_month(month_key, -1))
    prev_totals = _totals(db, user.id, prev_start, prev_end)

    current_budget = db.scalar(
        select(Budget).where(Budget.user_id == user.id, Budget.month == start).limit(1)
    )
    budget_attention: list[dict] = []
    if current_budget is not None:
        for entry in progress_for(db, user.id, [current_budget]):
            for item in entry["items"]:
                if item["pct_used"] >= 75:
                    budget_attention.append(
                        {
                            "budget_id": entry["id"],
                            "item_id": item["item_id"],
                            "category_name": item["category_name"],
                            "pct_used": item["pct_used"],
                        }
                    )

    recent_stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(8)
    )
    goals = db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user.id)).all()

    upcoming_cutoff = today_ + timedelta(days=7)
    upcoming_rules = db.scalars(
        select(RecurringTransaction).where(
            RecurringTransaction.user_id == user.id,
            RecurringTransaction.active.is_(True),
            RecurringTransaction.next_run_date <= upcoming_cutoff,
        )
    ).all()

    return {
        "balance_total": balance,
        "month_totals": totals,
        "previous_month_totals": prev_totals,
        "spending_series": _spending_series(db, user.id, month_key),
        "budget_attention": budget_attention,
        "recent_transactions": transactions_to_list(db, db.scalars(recent_stmt).all()),
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "target_amount": round(float(g.target_amount), 2),
                "current_amount": round(float(g.current_amount), 2),
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "color": g.color,
                "group_id": g.group_id,
            }
            for g in goals
        ],
        "upcoming_recurring": [
            {
                "id": r.id,
                "payee": r.payee,
                "amount": round(float(r.amount), 2),
                "next_run_date": r.next_run_date.isoformat(),
                "frequency": str(r.frequency.value),
            }
            for r in upcoming_rules
        ],
        "currency": user.currency,
    }
