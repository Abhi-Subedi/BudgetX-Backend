from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_preferences import NotificationPreferences
from app.models.user_preferences import UserPreferences


def get_or_create_preferences(db: Session, user_id: int) -> UserPreferences:
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    prefs = db.scalar(stmt)
    if prefs is None:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_preferences(db: Session, user_id: int, data: dict) -> UserPreferences:
    prefs = get_or_create_preferences(db, user_id)
    for field in ("language", "currency", "timezone", "theme", "date_format", "number_format"):
        if field in data and data[field] is not None:
            setattr(prefs, field, data[field])
    db.commit()
    db.refresh(prefs)
    return prefs


def get_or_create_notification_prefs(db: Session, user_id: int) -> NotificationPreferences:
    stmt = select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
    prefs = db.scalar(stmt)
    if prefs is None:
        prefs = NotificationPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_notification_prefs(db: Session, user_id: int, data: dict) -> NotificationPreferences:
    prefs = get_or_create_notification_prefs(db, user_id)
    for field in (
        "budget_alerts",
        "overspending_alerts",
        "bill_reminders",
        "goal_reminders",
        "weekly_summary",
        "monthly_summary",
        "security_alerts",
        "marketing",
    ):
        if field in data and data[field] is not None:
            setattr(prefs, field, data[field])
    db.commit()
    db.refresh(prefs)
    return prefs
