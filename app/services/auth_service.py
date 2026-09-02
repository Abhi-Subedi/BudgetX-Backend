import secrets
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import (
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_CATEGORIES,
    Account,
    AccountType,
    Category,
    CategoryKind,
    User,
)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def _seed_categories(db: Session, user: User) -> None:
    for name, color in DEFAULT_EXPENSE_CATEGORIES:
        db.add(Category(user_id=user.id, name=name, kind=CategoryKind.expense, color=color))
    for name, color in DEFAULT_INCOME_CATEGORIES:
        db.add(Category(user_id=user.id, name=name, kind=CategoryKind.income, color=color))


def _seed_accounts(db: Session, user: User) -> None:
    default_accounts = [
        ("Cash", AccountType.cash),
        ("Bank Account", AccountType.bank),
        ("Wallet", AccountType.wallet),
        ("Credit", AccountType.credit),
        ("Savings", AccountType.savings),
        ("Investment Account", AccountType.investment),
    ]

    for name, account_type in default_accounts:
        db.add(
            Account(
                user_id=user.id,
                name=name,
                type=account_type,
                currency=user.currency,
            )
        )


def register(db: Session, *, name: str, email: str, password: str, currency: str, locale: str) -> User:
    if get_by_email(db, email) is not None:
        raise AppError(409, "An account with this email already exists.")
    user = User(
        name=name.strip(),
        email=email.lower(),
        password_hash=hash_password(password),
        currency=currency.upper(),
        locale=locale,
    )
    db.add(user)
    db.flush()
    _seed_categories(db, user)
    _seed_accounts(db, user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "Incorrect email or password.")
    if not user.is_active:
        raise AppError(403, "This account has been deactivated.")
    return user


def issue_tokens(user: User) -> dict[str, str]:
    subject = str(user.id)
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
    }


def refresh_tokens(db: Session, refresh_token: str) -> dict[str, str]:
    user_id = decode_token(refresh_token, expected_type="refresh")
    user = get_by_id(db, int(user_id))
    if user is None or not user.is_active:
        raise AppError(401, "Invalid session. Please sign in again.")
    return issue_tokens(user)


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AppError(400, "Your current password is incorrect.")
    user.password_hash = hash_password(new_password)
    db.commit()


def generate_invite_code(db: Session) -> str:
    from app.models import Group

    for _ in range(10):
        code = secrets.token_hex(4)
        exists = db.scalar(select(func.count()).select_from(Group).where(Group.invite_code == code))
        if not exists:
            return code
    raise AppError(500, "Could not generate an invite code. Please try again.")


_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def add_months(d: date, months: int) -> date:
    index = (d.month - 1) + months
    year = d.year + index // 12
    month = index % 12 + 1
    return date(year, month, min(d.day, _days_in_month(year, month)))


def next_occurrence(d: date, frequency: str) -> date:
    from app.models.enums import Frequency

    if frequency == Frequency.daily:
        return d + timedelta(days=1)
    if frequency == Frequency.weekly:
        return d + timedelta(weeks=1)
    if frequency == Frequency.yearly:
        return add_months(d, 12)
    return add_months(d, 1)
