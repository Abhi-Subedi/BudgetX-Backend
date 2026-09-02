from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import Budget, BudgetItem, Category, Transaction
from app.models.enums import TransactionType
from app.schemas import BudgetCreate, BudgetUpdate
from app.services.common import get_owned


def _month_bounds(month_start: date) -> tuple[date, date]:
    if month_start.month == 12:
        return month_start, date(month_start.year + 1, 1, 1)
    return month_start, date(month_start.year, month_start.month + 1, 1)


def list_budgets(db: Session, user_id: int) -> list[Budget]:
    stmt = (
        select(Budget)
        .options(joinedload(Budget.items))
        .where(Budget.user_id == user_id)
        .order_by(Budget.month.desc(), Budget.id.desc())
    )
    return list(db.scalars(stmt).unique().all())


def get_budget(db: Session, user_id: int, budget_id: int) -> Budget:
    budget = get_owned(db, Budget, budget_id, user_id, "Budget")
    return budget


def create_budget(db: Session, user_id: int, data: BudgetCreate) -> Budget:
    month = data.month.replace(day=1)
    existing = db.scalar(select(func.count()).select_from(Budget).where(Budget.user_id == user_id, Budget.month == month))
    if existing:
        raise AppError(409, f"You already have a budget for {month.strftime('%B %Y')}. Edit it instead.")
    _validate_items(db, user_id, data.items)
    budget = Budget(user_id=user_id, name=data.name.strip() or "Monthly budget", month=month)
    db.add(budget)
    db.flush()
    for item in data.items:
        db.add(BudgetItem(budget_id=budget.id, category_id=item.category_id, amount=item.amount))
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(db: Session, user_id: int, budget_id: int, data: BudgetUpdate) -> Budget:
    budget = get_budget(db, user_id, budget_id)
    if data.name is not None:
        budget.name = data.name.strip() or "Monthly budget"
    if data.items is not None:
        _validate_items(db, user_id, data.items)
        budget.items.clear()
        db.flush()
        for item in data.items:
            db.add(BudgetItem(budget_id=budget.id, category_id=item.category_id, amount=item.amount))
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, user_id: int, budget_id: int) -> None:
    budget = get_budget(db, user_id, budget_id)
    db.delete(budget)
    db.commit()


def _validate_items(db: Session, user_id: int, items) -> None:
    from app.models.enums import CategoryKind

    if not items:
        raise AppError(422, "Budget needs at least one category amount.")
    for item in items:
        category = db.get(Category, item.category_id)
        if category is None or category.user_id != user_id:
            raise AppError(404, "One of the selected categories could not be found.")
        if category.kind != CategoryKind.expense:
            raise AppError(422, "Budget categories must be expense categories.")


def spent_by_category(db: Session, user_id: int, start: date, end: date) -> dict[int, float]:
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
    return {cid: round(float(total), 2) for cid, total in rows}


def days_left_in_month(today_: date | None = None) -> int:
    today_ = today_ or date.today()
    _, end = _month_bounds(today_.replace(day=1))
    return (end - today_).days - 1


def progress_for(db: Session, user_id: int, budgets: list[Budget]) -> list[dict]:
    result = []
    spent_cache: dict[str, dict[int, float]] = {}

    def spent_map(month: date) -> dict[int, float]:
        key = month.isoformat()
        if key not in spent_cache:
            start, end = _month_bounds(month)
            spent_cache[key] = spent_by_category(db, user_id, start, end)
        return spent_cache[key]

    for budget in budgets:
        smap = spent_map(budget.month)
        total_budget = 0.0
        total_spent = 0.0
        items_out = []
        for item in sorted(budget.items, key=lambda i: i.id):
            category = db.get(Category, item.category_id)
            budgeted = round(float(item.amount or 0), 2)
            spent = round(smap.get(item.category_id, 0.0), 2)
            remaining = round(budgeted - spent, 2)
            pct = round(spent / budgeted * 100, 1) if budgeted > 0 else 100.0
            total_budget += budgeted
            total_spent += spent
            items_out.append(
                {
                    "item_id": item.id,
                    "category_id": item.category_id,
                    "category_name": category.name if category else "Unknown",
                    "category_color": category.color if category else "#6E685C",
                    "budgeted": budgeted,
                    "spent": spent,
                    "remaining": remaining,
                    "pct_used": min(pct, 999),
                }
            )
        is_current = budget.month == date.today().replace(day=1)
        result.append(
            {
                "id": budget.id,
                "name": budget.name,
                "month": budget.month,
                "total_budget": round(total_budget, 2),
                "total_spent": round(total_spent, 2),
                "days_left": days_left_in_month() if is_current else 0,
                "items": sorted(items_out, key=lambda i: -i["pct_used"]),
            }
        )
    return result
