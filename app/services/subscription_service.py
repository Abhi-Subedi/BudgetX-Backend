import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Subscription
from app.models.enums import SubscriptionFrequency
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.services.common import get_owned

logger = logging.getLogger("budgetx")

_FREQUENCY_MONTHLY_MULTIPLIER = {
    SubscriptionFrequency.weekly: 4,
    SubscriptionFrequency.monthly: 1,
    SubscriptionFrequency.quarterly: 1 / 3,
    SubscriptionFrequency.yearly: 1 / 12,
}


def list_subscriptions(db: Session, user_id: int) -> list[Subscription]:
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.next_billing_date)
    )
    return list(db.scalars(stmt).all())


def get_subscription(db: Session, user_id: int, sub_id: int) -> Subscription:
    return get_owned(db, Subscription, sub_id, user_id, "Subscription")


def create_subscription(db: Session, user_id: int, data: SubscriptionCreate) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        name=data.name,
        amount=data.amount,
        frequency=data.frequency,
        category=data.category,
        next_billing_date=data.next_billing_date,
        start_date=data.start_date,
        end_date=data.end_date,
        account_id=data.account_id,
        notes=data.notes,
        logo_url=data.logo_url,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_subscription(db: Session, user_id: int, sub_id: int, data: SubscriptionUpdate) -> Subscription:
    sub = get_owned(db, Subscription, sub_id, user_id, "Subscription")
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, user_id: int, sub_id: int) -> None:
    sub = get_owned(db, Subscription, sub_id, user_id, "Subscription")
    db.delete(sub)
    db.commit()


def toggle_active(db: Session, user_id: int, sub_id: int) -> Subscription:
    sub = get_owned(db, Subscription, sub_id, user_id, "Subscription")
    sub.is_active = not sub.is_active
    db.commit()
    db.refresh(sub)
    return sub


def cancel(db: Session, user_id: int, sub_id: int) -> Subscription:
    sub = get_owned(db, Subscription, sub_id, user_id, "Subscription")
    sub.is_active = False
    sub.end_date = date.today()
    db.commit()
    db.refresh(sub)
    return sub


def get_summary(db: Session, user_id: int) -> dict:
    subs = list_subscriptions(db, user_id)
    active = [s for s in subs if s.is_active]

    monthly_cost = sum(
        float(s.amount) * _FREQUENCY_MONTHLY_MULTIPLIER.get(s.frequency, 1)
        for s in active
    )
    annual_cost = monthly_cost * 12

    return {
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(annual_cost, 2),
        "total_count": len(subs),
        "active_count": len(active),
    }


def get_upcoming_renewals(db: Session, user_id: int, days: int = 7) -> list[Subscription]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
            Subscription.next_billing_date <= cutoff,
        )
        .order_by(Subscription.next_billing_date)
    )
    return list(db.scalars(stmt).all())
