import hashlib
import hmac
import secrets
import time
import urllib.parse
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import verify_password
from app.models.backup_code import BackupCode
from app.models.totp import TOTPSecret
from app.models.user import User

_TOTP_PERIOD = 30
_TOTP_DIGITS = 6
_TOTP_WINDOW = 1


def generate_secret() -> str:
    return secrets.token_bytes(20).hex().upper()


def _generate_code(secret: str, timestamp: int | None = None) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    counter = timestamp // _TOTP_PERIOD
    counter_bytes = counter.to_bytes(8, "big")
    key = bytes.fromhex(secret)
    digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    code_int = code_int % (10 ** _TOTP_DIGITS)
    return str(code_int).zfill(_TOTP_DIGITS)


def get_qr_code_uri(secret: str, email: str, issuer: str = "BudgetX") -> str:
    label = f"{issuer}:{email}"
    params = urllib.parse.urlencode({"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": _TOTP_DIGITS, "period": _TOTP_PERIOD})
    return f"otpauth://totp/{urllib.parse.quote(label)}?{params}"


def verify_code(secret: str, code: str) -> bool:
    now = int(time.time())
    for offset in range(-_TOTP_WINDOW, _TOTP_WINDOW + 1):
        expected = _generate_code(secret, now + offset * _TOTP_PERIOD)
        if hmac.compare_digest(code, expected):
            return True
    return False


def enable_totp(db: Session, user_id: int, secret: str, code: str) -> TOTPSecret:
    if not verify_code(secret, code):
        raise AppError(400, "Invalid TOTP code. Please try again.")
    existing = db.scalar(select(TOTPSecret).where(TOTPSecret.user_id == user_id))
    if existing is not None:
        existing.secret = secret
        existing.enabled = True
        totp = existing
    else:
        totp = TOTPSecret(user_id=user_id, secret=secret, enabled=True)
        db.add(totp)
    user = db.get(User, user_id)
    if user is not None:
        user.two_factor_enabled = True
    db.commit()
    db.refresh(totp)
    return totp


def disable_totp(db: Session, user_id: int, password: str) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "User not found.")
    if user.password_hash is None or not verify_password(password, user.password_hash):
        raise AppError(400, "Your password is incorrect.")
    totp = db.scalar(select(TOTPSecret).where(TOTPSecret.user_id == user_id))
    if totp is not None:
        db.delete(totp)
    user.two_factor_enabled = False
    stmt = select(BackupCode).where(BackupCode.user_id == user_id)
    for bc in db.scalars(stmt).all():
        db.delete(bc)
    db.commit()


def generate_backup_codes(db: Session, user_id: int, count: int = 10) -> list[str]:
    raw_codes: list[str] = []
    for _ in range(count):
        code = secrets.token_urlsafe(10)
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        bc = BackupCode(user_id=user_id, code_hash=code_hash)
        db.add(bc)
        raw_codes.append(code)
    db.commit()
    return raw_codes


def verify_backup_code(db: Session, user_id: int, code: str) -> bool:
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    stmt = select(BackupCode).where(
        BackupCode.user_id == user_id,
        BackupCode.used.is_(False),
    )
    for bc in db.scalars(stmt).all():
        if hmac.compare_digest(bc.code_hash, code_hash):
            bc.used = True
            bc.used_at = datetime.now(timezone.utc)
            db.commit()
            return True
    return False


def get_backup_codes(db: Session, user_id: int) -> list[BackupCode]:
    stmt = (
        select(BackupCode)
        .where(BackupCode.user_id == user_id, BackupCode.used.is_(False))
        .order_by(BackupCode.created_at)
    )
    return list(db.scalars(stmt).all())
