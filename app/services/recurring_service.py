import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Notification, RecurringTransaction, Transaction
from app.models.enums import Frequency, TransactionType
from app.schemas import RecurringCreate, RecurringUpdate
from app.services.auth_service import next_occurrence
from app.services.common import get_owned

logger = logging.getLogger("budgetx")

_MAX_CATCHUP = 60


def list_recurring(db: Session, user_id: int) -> list[RecurringTransaction]:
    stmt = (
        select(RecurringTransaction)
        .where(RecurringTransaction.user_id == user_id)
        .order_by(RecurringTransaction.next_run_date)
    )
    return list(db.scalars(stmt).all())


def create_recurring(db: Session, user_id: int, data: RecurringCreate) -> RecurringTransaction:
    from app.models import Category
    from app.services.account_service import ensure_account

    ensure_account(db, user_id, data.account_id)
    if data.category_id is not None:
        category = db.get(Category, data.category_id)
        if category is None or category.user_id != user_id:
            raise AppError(404, "Category not found.")
    rule = RecurringTransaction(
        user_id=user_id,
        account_id=data.account_id,
        category_id=data.category_id,
        type=data.type,
        amount=data.amount,
        frequency=data.frequency,
        next_run_date=data.next_run_date,
        end_date=data.end_date,
        payee=data.payee,
        note=data.note,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_recurring(db: Session, user_id: int, rule_id: int, data: RecurringUpdate) -> RecurringTransaction:
    rule = get_owned(db, RecurringTransaction, rule_id, user_id, "Recurring transaction")
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_recurring(db: Session, user_id: int, rule_id: int) -> None:
    rule = get_owned(db, RecurringTransaction, rule_id, user_id, "Recurring transaction")
    db.delete(rule)
    db.commit()


def _post(db: Session, rule: RecurringTransaction, on_date: date) -> None:
    txn = Transaction(
        user_id=rule.user_id,
        account_id=rule.account_id,
        category_id=rule.category_id,
        type=rule.type,
        amount=rule.amount,
        occurred_at=on_date,
        payee=rule.payee,
        note=rule.note,
        recurring_id=rule.id,
    )
    db.add(txn)
    label = rule.payee or "A recurring transaction"
    db.add(
        Notification(
            user_id=rule.user_id,
            type="recurring",
            title=f"{label} posted",
            body=f"{label} was added to your activity automatically.",
        )
    )


def materialize_due(db: Session, user_id: int) -> int:
    today_ = date.today()
    rules = db.scalars(
        select(RecurringTransaction).where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.active.is_(True),
            RecurringTransaction.next_run_date <= today_,
        )
    ).all()
    posted = 0
    for rule in rules:
        iterations = 0
        while (
            rule.active
            and rule.next_run_date <= today_
            and (rule.end_date is None or rule.next_run_date <= rule.end_date)
            and iterations < _MAX_CATCHUP
        ):
            _post(db, rule, rule.next_run_date)
            rule.next_run_date = next_occurrence(rule.next_run_date, str(rule.frequency))
            posted += 1
            iterations += 1
        if rule.end_date is not None and rule.next_run_date > rule.end_date:
            rule.active = False
    if posted:
        db.commit()
    return posted
