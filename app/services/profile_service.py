from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.user import User
from app.models.user_profile import UserProfile


def get_or_create_profile(db: Session, user_id: int) -> UserProfile:
    stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = db.scalar(stmt)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, user_id: int, data: dict) -> UserProfile:
    profile = get_or_create_profile(db, user_id)
    for field in ("first_name", "last_name", "display_name", "bio", "date_of_birth"):
        if field in data and data[field] is not None:
            setattr(profile, field, data[field])
    db.commit()
    db.refresh(profile)
    return profile


def update_avatar(db: Session, user_id: int, avatar_url: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "User not found.")
    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    return user


def delete_avatar(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "User not found.")
    user.avatar_url = None
    db.commit()
    db.refresh(user)
    return user
