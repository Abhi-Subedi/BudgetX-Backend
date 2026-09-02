from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Debt, DebtPayment
from app.schemas import DebtCreate, DebtPaymentCreate, DebtUpdate
from app.services.common import get_owned


def list_debts(db: Session, user_id: int, status: str | None = None) -> list[Debt]:
    stmt = select(Debt).where(Debt.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Debt.status == status)
    return list(db.scalars(stmt.order_by(Debt.created_at)).all())


def create_debt(db: Session, user_id: int, data: DebtCreate) -> Debt:
    debt = Debt(
        user_id=user_id,
        name=data.name,
        debt_type=data.debt_type,
        principal=data.principal,
        interest_rate=data.interest_rate,
        minimum_payment=data.minimum_payment,
        due_day=data.due_day,
        remaining_balance=data.remaining_balance,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


def update_debt(db: Session, user_id: int, debt_id: int, data: DebtUpdate) -> Debt:
    debt = get_owned(db, Debt, debt_id, user_id, "Debt")
    if data.name is not None:
        debt.name = data.name.strip()
    if data.debt_type is not None:
        debt.debt_type = data.debt_type
    if data.interest_rate is not None:
        debt.interest_rate = data.interest_rate
    if data.minimum_payment is not None:
        debt.minimum_payment = data.minimum_payment
    if data.due_day is not None:
        debt.due_day = data.due_day
    if data.end_date is not None:
        debt.end_date = data.end_date
    if data.status is not None:
        debt.status = data.status
    db.commit()
    db.refresh(debt)
    return debt


def delete_debt(db: Session, user_id: int, debt_id: int) -> None:
    debt = get_owned(db, Debt, debt_id, user_id, "Debt")
    db.delete(debt)
    db.commit()


def make_payment(db: Session, user_id: int, debt_id: int, data: DebtPaymentCreate) -> DebtPayment:
    debt = get_owned(db, Debt, debt_id, user_id, "Debt")
    if debt.status != "active":
        raise AppError(400, "Cannot make payment on a non-active debt.")
    if data.amount > debt.remaining_balance:
        raise AppError(400, "Payment amount exceeds remaining balance.")
    payment = DebtPayment(
        debt_id=debt.id,
        amount=data.amount,
        payment_date=data.payment_date,
        note=data.note,
    )
    db.add(payment)
    debt.remaining_balance = round(float(debt.remaining_balance) - data.amount, 2)
    if debt.remaining_balance <= 0:
        debt.remaining_balance = 0
        debt.status = "paid_off"
    db.commit()
    db.refresh(payment)
    db.refresh(debt)
    return payment


def get_debt_summary(db: Session, user_id: int) -> dict:
    debts = list_debts(db, user_id)
    total_remaining = round(sum(float(d.remaining_balance) for d in debts), 2)
    monthly_payments = round(sum(float(d.minimum_payment) for d in debts), 2)
    total_paid = round(
        sum(
            float(p.amount)
            for d in debts
            for p in db.scalars(
                select(DebtPayment).where(DebtPayment.debt_id == d.id)
            ).all()
        ),
        2,
    )
    active_debts = sum(1 for d in debts if d.status == "active")
    return {
        "total_debt": round(sum(float(d.principal) for d in debts), 2),
        "total_paid": total_paid,
        "total_remaining": total_remaining,
        "active_debts": active_debts,
        "monthly_payments": monthly_payments,
        "debts": debts,
    }
