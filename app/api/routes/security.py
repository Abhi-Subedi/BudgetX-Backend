from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models.user_session import UserSession
from app.schemas.auth import PasswordChangeIn
from app.services import auth_service

router = APIRouter(prefix="/security", tags=["security"])


@router.get("")
def get_security_summary(user: CurrentUser, db: DbSession):
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
    ).all()

    from app.models.totp import TOTPSecret

    totp = db.scalar(
        select(TOTPSecret).where(TOTPSecret.user_id == user.id)
    )

    from app.models.oauth_account import OAuthAccount

    providers = db.scalars(
        select(OAuthAccount.provider).where(OAuthAccount.user_id == user.id)
    ).all()

    last_login = db.scalar(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .order_by(UserSession.created_at.desc())
        .limit(1)
    )

    return {
        "last_login_at": last_login.created_at.isoformat() if last_login else None,
        "active_sessions_count": len(sessions),
        "two_factor_enabled": totp.enabled if totp else False,
        "connected_providers": list(providers),
    }


@router.post("/change-password")
def change_password(payload: PasswordChangeIn, user: CurrentUser, db: DbSession):
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return {"ok": True}


@router.get("/sessions")
def list_sessions(user: CurrentUser, db: DbSession):
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
    ).all()

    return [
        {
            "id": s.id,
            "device_name": s.device_name,
            "device_type": s.device_type,
            "browser": s.browser,
            "operating_system": s.operating_system,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat(),
            "last_active_at": s.last_active_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, user: CurrentUser, db: DbSession):
    from app.models.mixins import utcnow

    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id:
        raise AppError(404, "Session not found.")
    if session.revoked_at is not None:
        raise AppError(400, "Session is already revoked.")

    session.revoked_at = utcnow()
    db.commit()
    return {"ok": True}


@router.post("/logout-all")
def revoke_all_sessions(user: CurrentUser, db: DbSession):
    from app.models.mixins import utcnow

    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
    ).all()

    now = utcnow()
    for session in sessions:
        session.revoked_at = now

    db.commit()
    return {"ok": True, "revoked_count": len(sessions)}
