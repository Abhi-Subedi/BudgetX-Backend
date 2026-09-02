from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.bill import BillCreate, BillUpdate
from app.services import bill_service

router = APIRouter(prefix="/bills", tags=["bills"])


def _bill_dict(bill) -> dict:
    return {
        "id": bill.id,
        "user_id": bill.user_id,
        "name": bill.name,
        "amount": round(float(bill.amount), 2),
        "category": bill.category,
        "due_date": bill.due_date.isoformat(),
        "frequency": bill.frequency.value if hasattr(bill.frequency, "value") else str(bill.frequency),
        "is_paid": bill.is_paid,
        "paid_date": bill.paid_date.isoformat() if bill.paid_date else None,
        "account_id": bill.account_id,
        "notes": bill.notes,
        "reminder_days_before": bill.reminder_days_before,
        "auto_pay": bill.auto_pay,
        "status": bill.status.value if hasattr(bill.status, "value") else str(bill.status),
        "created_at": bill.created_at.isoformat() if hasattr(bill.created_at, "isoformat") else str(bill.created_at),
        "updated_at": bill.updated_at.isoformat() if hasattr(bill.updated_at, "isoformat") else str(bill.updated_at),
    }


@router.get("")
def list_bills(user: CurrentUser, db: DbSession):
    return {"items": [_bill_dict(b) for b in bill_service.list_bills(db, user.id)]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_bill(payload: BillCreate, user: CurrentUser, db: DbSession):
    return _bill_dict(bill_service.create_bill(db, user.id, payload))


@router.get("/upcoming")
def get_upcoming(user: CurrentUser, db: DbSession, days: int = Query(default=30, ge=1, le=365)):
    return {"items": [_bill_dict(b) for b in bill_service.get_upcoming(db, user.id, days)]}


@router.get("/overdue")
def get_overdue(user: CurrentUser, db: DbSession):
    return {"items": [_bill_dict(b) for b in bill_service.get_overdue(db, user.id)]}


@router.get("/summary")
def get_summary(user: CurrentUser, db: DbSession):
    return bill_service.get_bill_summary(db, user.id)


@router.get("/{bill_id}")
def get_bill(bill_id: int, user: CurrentUser, db: DbSession):
    return _bill_dict(bill_service.get_bill(db, user.id, bill_id))


@router.put("/{bill_id}")
def update_bill(bill_id: int, payload: BillUpdate, user: CurrentUser, db: DbSession):
    return _bill_dict(bill_service.update_bill(db, user.id, bill_id, payload))


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: int, user: CurrentUser, db: DbSession):
    bill_service.delete_bill(db, user.id, bill_id)


@router.post("/{bill_id}/pay")
def mark_as_paid(bill_id: int, user: CurrentUser, db: DbSession):
    return _bill_dict(bill_service.mark_as_paid(db, user.id, bill_id))
