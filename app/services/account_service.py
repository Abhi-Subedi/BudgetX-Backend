from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Account, AccountType
from app.models import Transaction

from app.schemas import AccountCreate, AccountUpdate

from app.services.common import (
    account_balance,
    get_owned,
    total_balance,
)


def list_accounts(
    db: Session,
    user_id: int,
    include_archived: bool = True,
) -> list[Account]:

    stmt = select(Account).where(
        Account.user_id == user_id
    )

    if not include_archived:
        stmt = stmt.where(
            Account.archived.is_(False)
        )

    return list(
        db.scalars(
            stmt.order_by(Account.created_at)
        ).all()
    )


def create_account(
    db: Session,
    user_id: int,
    data: AccountCreate,
) -> Account:

    account = Account(
        user_id=user_id,
        name=data.name,
        type=data.type,
        currency=data.currency,
        opening_balance=data.opening_balance,
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


def update_account(
    db: Session,
    user_id: int,
    account_id: int,
    data: AccountUpdate,
) -> Account:

    account = get_owned(
        db,
        Account,
        account_id,
        user_id,
        "Account",
    )

    if data.name is not None:
        account.name = data.name.strip()

    if data.archived is not None:
        account.archived = data.archived

    db.commit()
    db.refresh(account)

    return account


def delete_account(
    db: Session,
    user_id: int,
    account_id: int,
) -> None:

    account = get_owned(
        db,
        Account,
        account_id,
        user_id,
        "Account",
    )

    count = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.account_id == account.id
        )
    )

    if count and count > 0:
        raise AppError(
            409,
            "This account has transactions. "
            "Delete or move them first.",
        )

    db.delete(account)
    db.commit()


def ensure_account(
    db: Session,
    user_id: int,
    account_id: int,
) -> Account:

    return get_owned(
        db,
        Account,
        account_id,
        user_id,
        "Account",
    )


def first_active_account(
    db: Session,
    user_id: int,
) -> Account | None:

    return db.scalar(
        select(Account)
        .where(
            Account.user_id == user_id,
            Account.archived.is_(False),
        )
        .order_by(Account.created_at)
    )


def with_balances(
    db: Session,
    accounts: list[Account],
) -> list[dict]:

    result = []

    for account in accounts:
        result.append(
            {
                "id": account.id,
                "name": account.name,
                "type": (
                    account.type.value
                    if isinstance(account.type, AccountType)
                    else account.type
                ),
                "currency": account.currency,
                "opening_balance": float(
                    account.opening_balance
                ),
                "archived": account.archived,
                "created_at": account.created_at,
                "updated_at": account.updated_at,
                "balance": account_balance(
                    db,
                    account,
                ),
            }
        )

    return result


# ============================================================
# USER ACCOUNT DELETION
# ============================================================

def delete_user_account(
    db: Session,
    user,
    password: str,
) -> None:
    """
    Permanently delete the authenticated user's account.

    Password verification must happen before any data is deleted.
    """

    if not password or not password.strip():
        raise AppError(
            400,
            "Password is required.",
        )

    # Import here to avoid unnecessary circular imports.
    from app.core.security import verify_password

    # --------------------------------------------------------
    # Verify password
    # --------------------------------------------------------

    if not verify_password(
        password,
        user.password_hash,
    ):
        raise AppError(
            401,
            "Incorrect password.",
        )

    user_id = user.id

    try:
        # ----------------------------------------------------
        # Delete user-owned data
        #
        # IMPORTANT:
        # These imports/queries assume these models exist and
        # contain user_id.
        # ----------------------------------------------------

        from app.models import (
            Budget,
            Category,
        )

        # Delete transactions
        db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        # Delete budgets
        db.query(Budget).filter(
            Budget.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        # Delete accounts
        db.query(Account).filter(
            Account.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        # Delete categories
        db.query(Category).filter(
            Category.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        # ----------------------------------------------------
        # Delete the user LAST
        # ----------------------------------------------------

        db.delete(user)

        # ----------------------------------------------------
        # Commit everything together
        # ----------------------------------------------------

        db.commit()

    except Exception:
        db.rollback()
        raise