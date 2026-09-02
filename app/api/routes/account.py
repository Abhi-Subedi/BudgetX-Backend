from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.core.security import verify_password
from app.models.user_profile import UserProfile

router = APIRouter(prefix="/account", tags=["account"])


class DeleteAccountIn(BaseModel):
    password: str


@router.delete("")
def delete_account(payload: DeleteAccountIn, user: CurrentUser, db: DbSession):
    if not user.password_hash:
        raise AppError(400, "No password set on this account.")
    if not verify_password(payload.password, user.password_hash):
        raise AppError(400, "Incorrect password.")

    user.status = "deleted"
    user.is_active = False
    db.commit()

    return {"ok": True}


@router.get("/export")
def export_data(user: CurrentUser, db: DbSession):
    profile = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )

    from app.models.account import Account
    from app.models.transaction import Transaction

    accounts = db.scalars(
        select(Account).where(Account.user_id == user.id)
    ).all()

    transactions = db.scalars(
        select(Transaction).where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(10000)
    ).all()

    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "currency": user.currency,
            "locale": user.locale,
            "created_at": user.created_at.isoformat(),
        },
        "profile": {
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "display_name": profile.display_name if profile else None,
            "bio": profile.bio if profile else None,
            "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        } if profile else None,
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type.value if hasattr(a.type, "value") else a.type,
                "currency": a.currency,
                "opening_balance": float(a.opening_balance),
            }
            for a in accounts
        ],
        "transactions": [
            {
                "id": t.id,
                "amount": float(t.amount),
                "type": t.type.value if hasattr(t.type, "value") else t.type,
                "payee": t.payee,
                "note": t.note,
                "occurred_at": t.occurred_at.isoformat(),
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    }

    return data
