import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.user import User
from app.models.user_session import UserSession


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_user_agent(user_agent: str | None) -> dict:
    if not user_agent:
        return {"device_type": "desktop", "browser": "Unknown", "operating_system": "Unknown"}

    ua = user_agent.lower()

    if any(k in ua for k in ("iphone", "ipad", "ipod")):
        device_type = "mobile"
        if "ipad" in ua:
            device_type = "tablet"
    elif any(k in ua for k in ("android",)):
        device_type = "mobile"
        if "tablet" in ua or "pad" in ua:
            device_type = "tablet"
    elif any(k in ua for k in ("mobile",)):
        device_type = "mobile"
    else:
        device_type = "desktop"

    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome" in ua and "safari" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    else:
        browser = "Unknown"

    if "windows" in ua:
        os = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os = "macOS"
    elif "linux" in ua and "android" not in ua:
        os = "Linux"
    elif "android" in ua:
        os = "Android"
    elif any(k in ua for k in ("iphone", "ipad", "ipod")):
        os = "iOS"
    else:
        os = "Unknown"

    return {"device_type": device_type, "browser": browser, "operating_system": os}


def create_session(
    db: Session, user: User, ip: str | None = None, user_agent: str | None = None
) -> UserSession:
    raw_token = hashlib.sha256(
        f"{user.id}:{datetime.now(timezone.utc).isoformat()}:{user_agent}".encode()
    ).hexdigest()
    token_hash = _hash_token(raw_token)
    parsed = _parse_user_agent(user_agent)
    now = datetime.now(timezone.utc)
    session = UserSession(
        user_id=user.id,
        session_token_hash=token_hash,
        device_type=parsed["device_type"],
        browser=parsed["browser"],
        operating_system=parsed["operating_system"],
        ip_address=ip,
        created_at=now,
        last_active_at=now,
        expires_at=now + timedelta(days=14),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_sessions(db: Session, user_id: int) -> list[UserSession]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_active_at.desc())
    )
    return list(db.scalars(stmt).all())


def revoke_session(db: Session, user_id: int, session_id: int) -> None:
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user_id:
        raise AppError(404, "Session not found.")
    if session.revoked_at is not None:
        return
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()


def revoke_all_sessions(db: Session, user_id: int, except_session_id: int | None = None) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
    )
    if except_session_id is not None:
        stmt = stmt.where(UserSession.id != except_session_id)
    stmt = stmt.values(revoked_at=now)
    db.execute(stmt)
    db.commit()


def validate_session(db: Session, token_hash: str) -> UserSession | None:
    now = datetime.now(timezone.utc)
    stmt = select(UserSession).where(
        UserSession.session_token_hash == token_hash,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > now,
    )
    session = db.scalar(stmt)
    if session is not None:
        session.last_active_at = now
        db.commit()
    return session


def cleanup_expired_sessions(db: Session) -> int:
    now = datetime.now(timezone.utc)
    stmt = select(UserSession).where(UserSession.expires_at <= now)
    expired = list(db.scalars(stmt).all())
    count = len(expired)
    for s in expired:
        db.delete(s)
    db.commit()
    return count
