import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import Budget, BudgetItem, Category, Transaction
from app.schemas import TransactionCreate, TransactionUpdate
from app.schemas.transaction import CsvTransactionRow
from app.services.account_service import ensure_account
from app.services.common import get_owned

logger = logging.getLogger("budgetx")


def _base_query(user_id: int):
    return (
        select(Transaction)
        .options(joinedload(Transaction.splits))
        .where(Transaction.user_id == user_id)
    )


def _apply_filters(
    stmt,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    type_: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    group_id: int | None = None,
    q: str | None = None,
):
    from app.models.enums import TransactionType

    if from_date is not None:
        stmt = stmt.where(Transaction.occurred_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Transaction.occurred_at <= to_date)
    if type_ is not None:
        try:
            stmt = stmt.where(Transaction.type == TransactionType(type_))
        except ValueError as exc:
            raise AppError(422, "Type must be expense or income.") from exc
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if group_id is not None:
        stmt = stmt.where(Transaction.group_id == group_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.outerjoin(Category, Category.id == Transaction.category_id).where(
            (Transaction.payee.ilike(pattern)) | (Transaction.note.ilike(pattern)) | (Category.name.ilike(pattern))
        )
    return stmt


def list_transactions(db: Session, user_id: int, *, page: int, page_size: int, **filters):
    stmt = _apply_filters(_base_query(user_id), **filters).order_by(
        Transaction.occurred_at.desc(), Transaction.id.desc()
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return rows, int(total)


def get_transaction(db: Session, user_id: int, transaction_id: int) -> Transaction:
    stmt = _base_query(user_id).where(Transaction.id == transaction_id)
    txn = db.scalar(stmt)
    if txn is None:
        raise AppError(404, "Transaction not found.")
    return txn


def _validate_refs(db: Session, user_id: int, account_id: int, category_id: int | None) -> None:
    ensure_account(db, user_id, account_id)
    if category_id is not None:
        category = db.get(Category, category_id)
        if category is None or category.user_id != user_id:
            raise AppError(404, "Category not found.")


def create_transaction(db: Session, user_id: int, data: TransactionCreate) -> Transaction:
    _validate_refs(db, user_id, data.account_id, data.category_id)
    txn = Transaction(
        user_id=user_id,
        account_id=data.account_id,
        category_id=data.category_id,
        type=data.type,
        amount=data.amount,
        occurred_at=data.occurred_at,
        payee=data.payee,
        note=data.note,
        group_id=None,
        created_by_id=user_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    _check_budget_thresholds(db, user_id, txn)
    return txn


def update_transaction(db: Session, user_id: int, transaction_id: int, data: TransactionUpdate) -> Transaction:
    txn = get_transaction(db, user_id, transaction_id)
    if txn.group_id is not None and data.account_id is not None:
        raise AppError(400, "Shared expenses cannot be moved between accounts.")
    payload = data.model_dump(exclude_unset=True)
    new_account = payload.get("account_id", txn.account_id)
    new_category = payload.get("category_id", txn.category_id)
    _validate_refs(db, user_id, new_account, new_category)
    for field, value in payload.items():
        setattr(txn, field, value)
    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, user_id: int, transaction_id: int) -> None:
    txn = get_transaction(db, user_id, transaction_id)
    db.delete(txn)
    db.commit()


def import_transactions(db: Session, user_id: int, rows: list[CsvTransactionRow]) -> int:
    created = 0
    for row in rows:
        _validate_refs(db, user_id, row.account_id, row.category_id)
        txn = Transaction(
            user_id=user_id,
            account_id=row.account_id,
            category_id=row.category_id,
            type=row.type,
            amount=row.amount,
            occurred_at=row.occurred_at,
            payee=row.payee,
            note=row.note,
            group_id=None,
            created_by_id=user_id,
        )
        db.add(txn)
        created += 1
    db.commit()
    return created


def spent_in_month_for_category(db: Session, user_id: int, month_start: date, month_end: date, category_id: int) -> float:
    from app.models.enums import TransactionType

    total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.category_id == category_id,
            Transaction.occurred_at >= month_start,
            Transaction.occurred_at < month_end,
        )
    )
    return round(float(total or 0), 2)


def _check_budget_thresholds(db: Session, user_id: int, txn: Transaction) -> None:
    from app.models import Notification

    if txn.type.value != "expense" or txn.category_id is None:
        return
    month_start = txn.occurred_at.replace(day=1)
    if txn.occurred_at.month == 12:
        month_end = date(txn.occurred_at.year + 1, 1, 1)
    else:
        month_end = date(txn.occurred_at.year, txn.occurred_at.month + 1, 1)

    item = db.scalar(
        select(BudgetItem)
        .join(Budget, Budget.id == BudgetItem.budget_id)
        .where(Budget.user_id == user_id, Budget.month == month_start, BudgetItem.category_id == txn.category_id)
    )
    if item is None:
        return

    after = spent_in_month_for_category(db, user_id, month_start, month_end, txn.category_id)
    budgeted = float(item.amount or 0)
    pct_after = (after / budgeted * 100) if budgeted > 0 else 0

    category = db.get(Category, txn.category_id)
    name = category.name if category else "Budget"

    already_notified = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.type == "budget",
            Notification.title.like(f"%{name}%"),
            Notification.created_at >= month_start,
        )
    )

    def notify(title: str, body: str, ntype: str) -> None:
        db.add(Notification(user_id=user_id, type=ntype, title=title, body=body))
        db.commit()

    if pct_after >= 100 and not already_notified:
        notify(f"{name} budget exceeded", f"You've gone over your {name} budget for this month.", "budget")
    elif pct_after >= 80 and (not already_notified):
        notify(f"{name} budget at {pct_after:.0f}%", f"You've used {pct_after:.0f}% of your {name} budget.", "budget")
