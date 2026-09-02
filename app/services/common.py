from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Account, Transaction, TransactionType


def get_owned(db: Session, model, entity_id: int, user_id: int, label: str):
    entity = db.get(model, entity_id)
    if entity is None or getattr(entity, "user_id", None) != user_id:
        raise AppError(404, f"{label} not found.")
    return entity


def account_balance(db: Session, account: Account) -> float:
    signed = case(
        (Transaction.type == TransactionType.income, Transaction.amount),
        else_=-Transaction.amount,
    )
    total = db.scalar(select(func.coalesce(func.sum(signed), 0)).where(Transaction.account_id == account.id))
    return round(float(account.opening_balance or 0) + float(total or 0), 2)


def total_balance(db: Session, user_id: int) -> float:
    accounts = db.scalars(
        select(Account).where(Account.user_id == user_id, Account.archived.is_(False))
    ).all()
    return round(sum(account_balance(db, a) for a in accounts), 2)


def month_bounds(month: str) -> tuple[date, date]:
    try:
        year_str, month_str = month.split("-")
        year, m = int(year_str), int(month_str)
        if not (2000 <= year <= 2200 and 1 <= m <= 12):
            raise ValueError
    except ValueError as exc:
        raise AppError(422, "Month must be formatted as YYYY-MM.") from exc
    start = date(year, m, 1)
    end = date(year + (m == 12), m % 12 + 1, 1)
    return start, end


def month_label(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def shift_month(month: str, delta: int) -> str:
    start, _ = month_bounds(month)
    from app.services.auth_service import add_months

    return month_label(add_months(start, delta))
