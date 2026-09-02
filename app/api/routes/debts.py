# app/api/debts.py (or app/routers/debts.py)

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.debt import Debt
from app.schemas.debt import DebtRead, DebtSummary

router = APIRouter(prefix="/debts", tags=["debts"])


# Schema for list response wrapper
class DebtListResponse(BaseModel):
    items: list[DebtRead]


@router.get("", response_model=DebtListResponse)
def get_debts(db: Session = Depends(get_db)):
    debts = db.query(Debt).all()
    # FastAPI automatically serializes SQLAlchemy Debt models into DebtRead objects
    return {"items": debts}


@router.get("/summary", response_model=DebtSummary)
def get_debt_summary(db: Session = Depends(get_db)):
    debts = db.query(Debt).all()
    
    total_debt = sum(d.principal for d in debts)
    total_remaining = sum(d.remaining_balance for d in debts)
    monthly_payments = sum(d.minimum_payment for d in debts if d.remaining_balance > 0)
    active_debts = sum(1 for d in debts if d.remaining_balance > 0)

    return DebtSummary(
        total_debt=total_debt,
        total_paid=total_debt - total_remaining,
        total_remaining=total_remaining,
        active_debts=active_debts,
        monthly_payments=monthly_payments,
        debts=debts,
    )