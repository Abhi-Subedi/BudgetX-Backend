import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models.user_profile import UserProfile

router = APIRouter(prefix="/profile", tags=["profile"])

UPLOAD_DIR = Path("uploads/avatars")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class ProfileUpdateIn(BaseModel):
    first_name: str | None = Field(default=None, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)
    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=500)
    date_of_birth: str | None = None


@router.get("")
def get_profile(user: CurrentUser, db: DbSession):
    profile = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "currency": user.currency,
            "locale": user.locale,
            "avatar_url": user.avatar_url,
        },
        "profile": {
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "display_name": profile.display_name if profile else None,
            "bio": profile.bio if profile else None,
            "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        } if profile else None,
    }


@router.patch("")
def update_profile(payload: ProfileUpdateIn, user: CurrentUser, db: DbSession):
    profile = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )

    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    data = payload.model_dump(exclude_unset=True)
    if "date_of_birth" in data and data["date_of_birth"] is not None:
        from datetime import date

        data["date_of_birth"] = date.fromisoformat(data["date_of_birth"])

    for field, value in data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "display_name": profile.display_name,
        "bio": profile.bio,
        "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
    }


@router.post("/avatar")
async def upload_avatar(user: CurrentUser, db: DbSession, file: UploadFile = File(...)):
    if not file.filename:
        raise AppError(400, "No file provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(400, f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise AppError(400, "File size exceeds 5MB limit.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{user.id}.{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    avatar_url = f"/uploads/avatars/{filename}"
    user.avatar_url = avatar_url
    db.commit()

    return {"avatar_url": avatar_url}


@router.delete("/avatar")
def delete_avatar(user: CurrentUser, db: DbSession):
    if not user.avatar_url:
        raise AppError(404, "No avatar to remove.")

    old_path = Path(user.avatar_url.lstrip("/"))
    if old_path.exists():
        old_path.unlink()

    user.avatar_url = None
    db.commit()

    return {"ok": True}
