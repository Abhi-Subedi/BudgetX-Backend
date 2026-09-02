from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.services import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _sub_dict(sub) -> dict:
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "name": sub.name,
        "amount": round(float(sub.amount), 2),
        "frequency": sub.frequency.value if hasattr(sub.frequency, "value") else str(sub.frequency),
        "category": sub.category,
        "next_billing_date": sub.next_billing_date.isoformat(),
        "start_date": sub.start_date.isoformat(),
        "end_date": sub.end_date.isoformat() if sub.end_date else None,
        "is_active": sub.is_active,
        "account_id": sub.account_id,
        "notes": sub.notes,
        "logo_url": sub.logo_url,
        "created_at": sub.created_at.isoformat() if hasattr(sub.created_at, "isoformat") else str(sub.created_at),
        "updated_at": sub.updated_at.isoformat() if hasattr(sub.updated_at, "isoformat") else str(sub.updated_at),
    }


@router.get("")
def list_subscriptions(user: CurrentUser, db: DbSession):
    return {"items": [_sub_dict(s) for s in subscription_service.list_subscriptions(db, user.id)]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, user: CurrentUser, db: DbSession):
    return _sub_dict(subscription_service.create_subscription(db, user.id, payload))


@router.get("/summary")
def get_summary(user: CurrentUser, db: DbSession):
    return subscription_service.get_summary(db, user.id)


@router.get("/upcoming")
def get_upcoming_renewals(user: CurrentUser, db: DbSession, days: int = Query(default=7, ge=1, le=90)):
    return {"items": [_sub_dict(s) for s in subscription_service.get_upcoming_renewals(db, user.id, days)]}


@router.get("/{sub_id}")
def get_subscription(sub_id: int, user: CurrentUser, db: DbSession):
    return _sub_dict(subscription_service.get_subscription(db, user.id, sub_id))


@router.put("/{sub_id}")
def update_subscription(sub_id: int, payload: SubscriptionUpdate, user: CurrentUser, db: DbSession):
    return _sub_dict(subscription_service.update_subscription(db, user.id, sub_id, payload))


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(sub_id: int, user: CurrentUser, db: DbSession):
    subscription_service.delete_subscription(db, user.id, sub_id)


@router.post("/{sub_id}/toggle")
def toggle_active(sub_id: int, user: CurrentUser, db: DbSession):
    return _sub_dict(subscription_service.toggle_active(db, user.id, sub_id))


@router.post("/{sub_id}/cancel")
def cancel(sub_id: int, user: CurrentUser, db: DbSession):
    return _sub_dict(subscription_service.cancel(db, user.id, sub_id))
