import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.backup_code import BackupCode
from app.models.totp import TOTPSecret

router = APIRouter(prefix="/2fa", tags=["2fa"])


class VerifyIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class DisableIn(BaseModel):
    password: str


def _generate_totp_secret(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def _generate_totp_uri(secret: str, email: str, issuer: str = "BudgetX") -> str:
    return f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def _verify_totp(secret: str, code: str) -> bool:
    import struct
    import time

    key = bytes.fromhex(secret) if len(secret) % 2 == 0 else secret.encode()
    counter = int(time.time()) // 30

    for offset in range(-1, 2):
        msg = struct.pack(">Q", counter + offset)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset_val = digest[-1] & 0x0F
        truncated = struct.unpack(">I", digest[offset_val : offset_val + 4])[0]
        truncated &= 0x7FFFFFFF
        otp = truncated % 1_000_000
        if otp == int(code):
            return True
    return False


def _generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


@router.post("/setup")
def setup_2fa(user: CurrentUser, db: DbSession):
    existing = db.scalar(
        select(TOTPSecret).where(TOTPSecret.user_id == user.id)
    )
    if existing and existing.enabled:
        raise AppError(400, "Two-factor authentication is already enabled.")

    secret = _generate_totp_secret()
    uri = _generate_totp_uri(secret, user.email)

    if existing:
        existing.secret = secret
        existing.enabled = False
    else:
        db.add(TOTPSecret(user_id=user.id, secret=secret, enabled=False))

    db.commit()
    return {"secret": secret, "uri": uri}


@router.post("/verify")
def verify_2fa(payload: VerifyIn, user: CurrentUser, db: DbSession):
    totp = db.scalar(
        select(TOTPSecret).where(TOTPSecret.user_id == user.id)
    )
    if totp is None:
        raise AppError(400, "Please set up 2FA first.")
    if totp.enabled:
        raise AppError(400, "Two-factor authentication is already enabled.")

    if not _verify_totp(totp.secret, payload.code):
        raise AppError(400, "Invalid verification code.")

    totp.enabled = True
    user.two_factor_enabled = True
    db.commit()

    raw_codes = _generate_backup_codes()
    for code in raw_codes:
        db.add(BackupCode(user_id=user.id, code_hash=hash_password(code)))
    db.commit()

    return {"ok": True, "backup_codes": raw_codes}


@router.post("/disable")
def disable_2fa(payload: DisableIn, user: CurrentUser, db: DbSession):
    if not user.password_hash:
        raise AppError(400, "No password set on this account.")
    if not verify_password(payload.password, user.password_hash):
        raise AppError(400, "Incorrect password.")

    totp = db.scalar(
        select(TOTPSecret).where(TOTPSecret.user_id == user.id)
    )
    if totp is None or not totp.enabled:
        raise AppError(400, "Two-factor authentication is not enabled.")

    totp.enabled = False
    user.two_factor_enabled = False

    from sqlalchemy import delete

    db.execute(delete(BackupCode).where(BackupCode.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.get("/backup-codes")
def get_backup_codes(user: CurrentUser, db: DbSession):
    codes = db.scalars(
        select(BackupCode).where(
            BackupCode.user_id == user.id,
            BackupCode.used == False,
        )
    ).all()

    return {
        "remaining": len(codes),
        "codes": [
            {"id": c.id, "created_at": c.created_at.isoformat()}
            for c in codes
        ],
    }


class RegenerateResponse(BaseModel):
    ok: bool = True
    backup_codes: list[str]


@router.post("/backup-codes/regenerate")
def regenerate_backup_codes(payload: DisableIn, user: CurrentUser, db: DbSession):
    if not user.password_hash:
        raise AppError(400, "No password set on this account.")
    if not verify_password(payload.password, user.password_hash):
        raise AppError(400, "Incorrect password.")

    if not user.two_factor_enabled:
        raise AppError(400, "Two-factor authentication is not enabled.")

    from sqlalchemy import delete

    db.execute(delete(BackupCode).where(BackupCode.user_id == user.id))
    db.flush()

    raw_codes = _generate_backup_codes()
    for code in raw_codes:
        db.add(BackupCode(user_id=user.id, code_hash=hash_password(code)))
    db.commit()

    return {"ok": True, "backup_codes": raw_codes}
