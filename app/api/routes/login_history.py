from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.login_event import LoginEvent

router = APIRouter(prefix="/login-history", tags=["login-history"])


@router.get("")
def list_login_events(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = (
        select(LoginEvent)
        .where(LoginEvent.user_id == user.id)
        .order_by(LoginEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = db.scalars(query).all()

    total = db.scalar(
        select(func.count()).select_from(LoginEvent).where(LoginEvent.user_id == user.id)
    )

    return {
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "ip_address": e.ip_address,
                "device": e.device,
                "browser": e.browser,
                "success": e.success,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/security-summary")
def security_summary(user: CurrentUser, db: DbSession):
    total = db.scalar(
        select(func.count()).select_from(LoginEvent).where(LoginEvent.user_id == user.id)
    )
    failed = db.scalar(
        select(func.count())
        .select_from(LoginEvent)
        .where(LoginEvent.user_id == user.id, LoginEvent.success == False)
    )
    last_event = db.scalar(
        select(LoginEvent)
        .where(LoginEvent.user_id == user.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(1)
    )
    unique_ips = db.scalar(
        select(func.count(func.distinct(LoginEvent.ip_address))).where(
            LoginEvent.user_id == user.id
        )
    )

    return {
        "total_logins": total or 0,
        "failed_attempts": failed or 0,
        "unique_ips": unique_ips or 0,
        "last_login_at": last_event.created_at.isoformat() if last_event else None,
        "last_login_ip": last_event.ip_address if last_event else None,
    }
