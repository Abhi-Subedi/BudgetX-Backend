from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.models.oauth_account import OAuthAccount
from app.models.user import User


def find_or_create_oauth_user(
    db: Session,
    provider: str,
    provider_user_id: str,
    email: str,
    name: str,
) -> tuple[User, bool]:
    stmt = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    oauth = db.scalar(stmt)
    if oauth is not None:
        oauth.last_used_at = datetime.now(timezone.utc)
        db.commit()
        user = db.get(User, oauth.user_id)
        return user, False

    user_stmt = select(User).where(User.email == email.lower())
    user = db.scalar(user_stmt)
    is_new = False
    if user is None:
        user = User(
            name=name.strip(),
            email=email.lower(),
            password_hash=None,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()
        is_new = True

    oauth = OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email.lower(),
    )
    db.add(oauth)
    db.commit()
    db.refresh(user)
    return user, is_new


def link_oauth_account(
    db: Session, user_id: int, provider: str, provider_user_id: str, email: str
) -> OAuthAccount:
    existing_stmt = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    existing = db.scalar(existing_stmt)
    if existing is not None:
        if existing.user_id != user_id:
            raise AppError(409, "This provider account is already linked to another user.")
        return existing

    user_oauth_stmt = select(OAuthAccount).where(
        OAuthAccount.user_id == user_id,
        OAuthAccount.provider == provider,
    )
    user_oauth = db.scalar(user_oauth_stmt)
    if user_oauth is not None:
        raise AppError(409, f"You already have a {provider} account linked.")

    oauth = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email.lower() if email else None,
    )
    db.add(oauth)
    db.commit()
    db.refresh(oauth)
    return oauth


def unlink_oauth_account(db: Session, user_id: int, provider: str) -> None:
    stmt = select(OAuthAccount).where(
        OAuthAccount.user_id == user_id,
        OAuthAccount.provider == provider,
    )
    oauth = db.scalar(stmt)
    if oauth is None:
        raise AppError(404, f"No {provider} account linked.")
    db.delete(oauth)
    db.commit()


def get_linked_providers(db: Session, user_id: int) -> list[dict]:
    stmt = (
        select(OAuthAccount)
        .where(OAuthAccount.user_id == user_id)
        .order_by(OAuthAccount.created_at)
    )
    accounts = list(db.scalars(stmt).all())
    return [
        {
            "provider": a.provider,
            "email": a.provider_email,
            "linked_at": a.created_at,
            "last_used_at": a.last_used_at,
        }
        for a in accounts
    ]
