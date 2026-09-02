from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.notification_preferences import NotificationPreferences
from app.models.user_preferences import UserPreferences

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferencesUpdateIn(BaseModel):
    language: str | None = Field(default=None, max_length=10)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=50)
    theme: str | None = Field(default=None, max_length=20)
    date_format: str | None = Field(default=None, max_length=20)
    number_format: str | None = Field(default=None, max_length=20)


class NotificationPrefsUpdateIn(BaseModel):
    budget_alerts: bool | None = None
    overspending_alerts: bool | None = None
    bill_reminders: bool | None = None
    goal_reminders: bool | None = None
    weekly_summary: bool | None = None
    monthly_summary: bool | None = None
    security_alerts: bool | None = None
    marketing: bool | None = None


def _get_or_create_preferences(db, user_id: int) -> UserPreferences:
    prefs = db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if prefs is None:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


def _get_or_create_notification_preferences(db, user_id: int) -> NotificationPreferences:
    prefs = db.scalar(select(NotificationPreferences).where(NotificationPreferences.user_id == user_id))
    if prefs is None:
        prefs = NotificationPreferences(user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


@router.get("")
def get_preferences(user: CurrentUser, db: DbSession):
    prefs = _get_or_create_preferences(db, user.id)
    db.commit()
    return {
        "language": prefs.language,
        "currency": prefs.currency,
        "timezone": prefs.timezone,
        "theme": prefs.theme,
        "date_format": prefs.date_format,
        "number_format": prefs.number_format,
    }


@router.patch("")
def update_preferences(payload: PreferencesUpdateIn, user: CurrentUser, db: DbSession):
    prefs = _get_or_create_preferences(db, user.id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return {
        "language": prefs.language,
        "currency": prefs.currency,
        "timezone": prefs.timezone,
        "theme": prefs.theme,
        "date_format": prefs.date_format,
        "number_format": prefs.number_format,
    }


@router.get("/notifications")
def get_notification_preferences(user: CurrentUser, db: DbSession):
    prefs = _get_or_create_notification_preferences(db, user.id)
    db.commit()
    return {
        "budget_alerts": prefs.budget_alerts,
        "overspending_alerts": prefs.overspending_alerts,
        "bill_reminders": prefs.bill_reminders,
        "goal_reminders": prefs.goal_reminders,
        "weekly_summary": prefs.weekly_summary,
        "monthly_summary": prefs.monthly_summary,
        "security_alerts": prefs.security_alerts,
        "marketing": prefs.marketing,
    }


@router.patch("/notifications")
def update_notification_preferences(payload: NotificationPrefsUpdateIn, user: CurrentUser, db: DbSession):
    prefs = _get_or_create_notification_preferences(db, user.id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return {
        "budget_alerts": prefs.budget_alerts,
        "overspending_alerts": prefs.overspending_alerts,
        "bill_reminders": prefs.bill_reminders,
        "goal_reminders": prefs.goal_reminders,
        "weekly_summary": prefs.weekly_summary,
        "monthly_summary": prefs.monthly_summary,
        "security_alerts": prefs.security_alerts,
        "marketing": prefs.marketing,
    }
