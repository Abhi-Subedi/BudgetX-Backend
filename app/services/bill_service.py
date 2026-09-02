import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Bill, Transaction
from app.models.enums import BillStatus, TransactionType
from app.schemas.bill import BillCreate, BillUpdate
from app.services.common import get_owned

logger = logging.getLogger("budgetx")


def list_bills(db: Session, user_id: int) -> list[Bill]:
    stmt = (
        select(Bill)
        .where(Bill.user_id == user_id)
        .order_by(Bill.due_date)
    )
    return list(db.scalars(stmt).all())


def get_bill(db: Session, user_id: int, bill_id: int) -> Bill:
    return get_owned(db, Bill, bill_id, user_id, "Bill")


def create_bill(db: Session, user_id: int, data: BillCreate) -> Bill:
    bill = Bill(
        user_id=user_id,
        name=data.name,
        amount=data.amount,
        category=data.category,
        due_date=data.due_date,
        frequency=data.frequency,
        account_id=data.account_id,
        notes=data.notes,
        reminder_days_before=data.reminder_days_before,
        auto_pay=data.auto_pay,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def update_bill(db: Session, user_id: int, bill_id: int, data: BillUpdate) -> Bill:
    bill = get_owned(db, Bill, bill_id, user_id, "Bill")
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(bill, field, value)
    db.commit()
    db.refresh(bill)
    return bill


def delete_bill(db: Session, user_id: int, bill_id: int) -> None:
    bill = get_owned(db, Bill, bill_id, user_id, "Bill")
    db.delete(bill)
    db.commit()


def mark_as_paid(db: Session, user_id: int, bill_id: int) -> Bill:
    bill = get_owned(db, Bill, bill_id, user_id, "Bill")
    today = date.today()
    bill.is_paid = True
    bill.paid_date = today
    bill.status = BillStatus.paid

    if bill.account_id is not None:
        txn = Transaction(
            user_id=user_id,
            account_id=bill.account_id,
            type=TransactionType.expense,
            amount=bill.amount,
            occurred_at=today,
            payee=bill.name,
            note=f"Bill payment: {bill.name}",
        )
        db.add(txn)

    db.commit()
    db.refresh(bill)
    return bill


def get_upcoming(db: Session, user_id: int, days: int = 30) -> list[Bill]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    stmt = (
        select(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.is_paid.is_(False),
            Bill.due_date <= cutoff,
            Bill.status != BillStatus.skipped,
        )
        .order_by(Bill.due_date)
    )
    return list(db.scalars(stmt).all())


def get_overdue(db: Session, user_id: int) -> list[Bill]:
    today = date.today()
    stmt = (
        select(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.is_paid.is_(False),
            Bill.due_date < today,
            Bill.status != BillStatus.skipped,
        )
        .order_by(Bill.due_date)
    )
    return list(db.scalars(stmt).all())


def get_bill_summary(db: Session, user_id: int) -> dict:
    today = date.today()
    all_bills = list_bills(db, user_id)
    unpaid = [b for b in all_bills if not b.is_paid]
    paid = [b for b in all_bills if b.is_paid]
    overdue = [b for b in unpaid if b.due_date < today]
    upcoming = [b for b in unpaid if b.due_date >= today]

    monthly_map = {
        "monthly": 1,
        "weekly": 4,
        "yearly": 12,
        "one_time": 1,
    }
    total_monthly = sum(
        float(b.amount) * monthly_map.get(b.frequency.value, 1)
        for b in unpaid
    )

    return {
        "total_monthly_obligations": round(total_monthly, 2),
        "total_pending": round(sum(float(b.amount) for b in unpaid), 2),
        "total_paid": round(sum(float(b.amount) for b in paid), 2),
        "total_overdue": round(sum(float(b.amount) for b in overdue), 2),
        "upcoming_count": len(upcoming),
        "overdue_count": len(overdue),
    }
