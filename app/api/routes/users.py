from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import UserUpdate
from app.schemas.auth import PasswordChangeIn
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user: CurrentUser):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "currency": user.currency,
        "locale": user.locale,
    }


@router.patch("/me")
def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "currency": user.currency,
        "locale": user.locale,
    }


@router.post("/me/password")
def change_password(payload: PasswordChangeIn, user: CurrentUser, db: DbSession):
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return {"ok": True}
