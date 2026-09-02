from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Account, Budget, BudgetItem, Category, Transaction, TransactionType
from app.models.enums import CategoryKind
from app.services.common import month_bounds, shift_month


def _get_monthly_totals(db: Session, user_id: int, start: date, end: date) -> tuple[float, float]:
    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=0.0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=0.0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).one()
    return round(float(income or 0), 2), round(float(expense or 0), 2)


def _savings_rate_score(db: Session, user_id: int, months: int = 6) -> float:
    today = date.today()
    rates = []
    for i in range(months):
        month_start = today.replace(day=1) - timedelta(days=30 * i)
        start, end = month_bounds(f"{month_start.year}-{month_start.month:02d}")
        income, expense = _get_monthly_totals(db, user_id, start, end)
        if income > 0:
            rate = (income - expense) / income * 100
            rates.append(max(0.0, min(100.0, rate)))
    avg_rate = sum(rates) / len(rates) if rates else 0.0
    return round(avg_rate, 1)


def _budget_adherence_score(db: Session, user_id: int) -> float:
    today = date.today()
    start, end = month_bounds(f"{today.year}-{today.month:02d}")
    budget = db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.month == start).limit(1))
    if budget is None:
        return 50.0
    items = db.scalars(select(BudgetItem).where(BudgetItem.budget_id == budget.id)).all()
    if not items:
        return 50.0
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
    total_budget = 0.0
    total_spent = 0.0
    for item in items:
        budgeted = round(float(item.amount or 0), 2)
        spent = spent_map.get(item.category_id, 0.0)
        total_budget += budgeted
        total_spent += spent
    if total_budget == 0:
        return 50.0
    ratio = total_spent / total_budget
    if ratio <= 1.0:
        return round(max(0.0, 100.0 - (1.0 - ratio) * 100.0), 1)
    overage = ratio - 1.0
    return round(max(0.0, 100.0 - overage * 200.0), 1)


def _debt_ratio_score(db: Session, user_id: int) -> float:
    today = date.today()
    start, end = month_bounds(f"{today.year}-{today.month:02d}")
    debt_payments = db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
            Transaction.category_id == Category.id,
            Category.kind == CategoryKind.expense,
            Category.name.ilike("%debt%"),
        )
    ).scalar()
    income = db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.income,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
    ).scalar()
    debt_f = round(float(debt_payments or 0), 2)
    income_f = round(float(income or 0), 2)
    if income_f == 0:
        return 50.0
    ratio = debt_f / income_f
    if ratio <= 0.2:
        return 100.0
    if ratio <= 0.5:
        return round(100.0 - (ratio - 0.2) / 0.3 * 50.0, 1)
    return round(max(0.0, 50.0 - (ratio - 0.5) * 100.0), 1)


def _emergency_fund_score(db: Session, user_id: int) -> float:
    today = date.today()
    start, end = month_bounds(f"{today.year}-{today.month:02d}")
    _, expense = _get_monthly_totals(db, user_id, start, end)
    if expense == 0:
        return 80.0
    accounts = db.scalars(select(Account).where(Account.user_id == user_id, Account.archived.is_(False))).all()
    from app.services.common import account_balance
    total_savings = 0.0
    for acc in accounts:
        if acc.type.value in ("savings", "cash"):
            total_savings += account_balance(db, acc)
    months_covered = total_savings / expense
    if months_covered >= 6:
        return 100.0
    if months_covered >= 3:
        return round(50.0 + (months_covered - 3) / 3 * 50.0, 1)
    return round(max(0.0, months_covered / 3 * 50.0), 1)


def _consistency_score(db: Session, user_id: int) -> float:
    today = date.today()
    streak = 0
    for i in range(12):
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        start, end = month_bounds(f"{month_date.year}-{month_date.month:02d}")
        income, expense = _get_monthly_totals(db, user_id, start, end)
        if income > 0 and income > expense:
            streak += 1
        else:
            break
    if streak >= 6:
        return 100.0
    if streak >= 3:
        return round(50.0 + (streak - 3) / 3 * 50.0, 1)
    return round(streak / 3 * 50.0, 1)


def _safe_score(func, db, user_id):
    try:
        return func(db, user_id)
    except Exception:
        return 50.0


def calculate_health_score(db: Session, user_id: int) -> dict:
    dimensions = {
        "savings_rate": _safe_score(_savings_rate_score, db, user_id),
        "budget_adherence": _safe_score(_budget_adherence_score, db, user_id),
        "debt_ratio": _safe_score(_debt_ratio_score, db, user_id),
        "emergency_fund": _safe_score(_emergency_fund_score, db, user_id),
        "consistency": _safe_score(_consistency_score, db, user_id),
    }
    weights = {"savings_rate": 0.25, "budget_adherence": 0.25, "debt_ratio": 0.2, "emergency_fund": 0.2, "consistency": 0.1}
    overall = round(sum(dimensions[k] * weights[k] for k in dimensions), 1)

    insights = []
    if dimensions["savings_rate"] < 40:
        insights.append("Your savings rate is low. Try to reduce discretionary spending.")
    if dimensions["budget_adherence"] < 50:
        insights.append("You're overspending relative to your budgets. Review your budget allocations.")
    if dimensions["debt_ratio"] > 60:
        insights.append("Your debt payments are taking a large portion of income. Consider a debt payoff plan.")
    if dimensions["emergency_fund"] < 50:
        insights.append("Your emergency fund could be stronger. Aim for 3-6 months of expenses.")
    if dimensions["consistency"] < 40:
        insights.append("Your saving streak is inconsistent. Try setting up automatic transfers.")

    return {"overall_score": overall, "dimensions": dimensions, "insights": insights}
