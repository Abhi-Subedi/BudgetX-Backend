from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.models.totp import TOTPSecret
from app.models.user import User
from app.models.user_session import UserSession
from app.services.oauth_service import get_linked_providers


def record_event(
    db: Session,
    user_id: int,
    event_type: str,
    ip: str | None = None,
    device: str | None = None,
    browser: str | None = None,
    success: bool = True,
) -> LoginEvent:
    event = LoginEvent(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip,
        device=device,
        browser=browser,
        success=success,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_history(
    db: Session, user_id: int, limit: int = 50, offset: int = 0
) -> list[LoginEvent]:
    stmt = (
        select(LoginEvent)
        .where(LoginEvent.user_id == user_id)
        .order_by(LoginEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


def get_security_summary(db: Session, user_id: int) -> dict:
    now = datetime.now(timezone.utc)

    last_event_stmt = (
        select(LoginEvent)
        .where(LoginEvent.user_id == user_id, LoginEvent.success.is_(True))
        .order_by(LoginEvent.created_at.desc())
        .limit(1)
    )
    last_event = db.scalar(last_event_stmt)
    last_login = last_event.created_at if last_event else None

    active_sessions = db.scalar(
        select(func.count()).select_from(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )

    totp = db.scalar(select(TOTPSecret).where(TOTPSecret.user_id == user_id))
    two_factor_enabled = totp is not None and totp.enabled

    providers = get_linked_providers(db, user_id)

    return {
        "last_login": last_login,
        "active_sessions_count": active_sessions or 0,
        "two_factor_enabled": two_factor_enabled,
        "connected_providers": [p["provider"] for p in providers],
    }
