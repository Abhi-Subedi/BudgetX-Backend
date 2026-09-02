from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import RecurringCreate, RecurringUpdate
from app.services import recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _rule_dict(rule) -> dict:
    return {
        "id": rule.id,
        "amount": round(float(rule.amount), 2),
        "type": rule.type.value if hasattr(rule.type, "value") else str(rule.type),
        "account_id": rule.account_id,
        "category_id": rule.category_id,
        "frequency": rule.frequency.value if hasattr(rule.frequency, "value") else str(rule.frequency),
        "next_run_date": rule.next_run_date.isoformat(),
        "end_date": rule.end_date.isoformat() if rule.end_date else None,
        "payee": rule.payee,
        "note": rule.note,
        "active": rule.active,
    }


@router.get("")
def list_recurring(user: CurrentUser, db: DbSession):
    return {"items": [_rule_dict(r) for r in recurring_service.list_recurring(db, user.id)]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recurring(payload: RecurringCreate, user: CurrentUser, db: DbSession):
    return _rule_dict(recurring_service.create_recurring(db, user.id, payload))


@router.put("/{rule_id}")
def update_recurring(rule_id: int, payload: RecurringUpdate, user: CurrentUser, db: DbSession):
    return _rule_dict(recurring_service.update_recurring(db, user.id, rule_id, payload))


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(rule_id: int, user: CurrentUser, db: DbSession):
    recurring_service.delete_recurring(db, user.id, rule_id)
