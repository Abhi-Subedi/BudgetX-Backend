from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.models.enums import CategoryKind
from app.schemas import AccountCreate, AccountUpdate
from app.services import account_service, category_service


router = APIRouter(tags=["accounts & categories"])


class AccountDeleteRequest(BaseModel):
    value: str


@router.get("/accounts")
def list_accounts(
    user: CurrentUser,
    db: DbSession,
    include_archived: bool = Query(default=True),
):
    accounts = account_service.list_accounts(
        db,
        user.id,
        include_archived=include_archived,
    )

    return {
        "items": account_service.with_balances(db, accounts),
        "total_balance": account_service.total_balance(db, user.id),
    }


@router.post(
    "/accounts",
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: AccountCreate,
    user: CurrentUser,
    db: DbSession,
):
    account = account_service.create_account(
        db,
        user.id,
        payload,
    )

    return account_service.with_balances(db, [account])[0]


@router.patch("/accounts/{account_id}")
def update_account(
    account_id: int,
    payload: AccountUpdate,
    user: CurrentUser,
    db: DbSession,
):
    account = account_service.update_account(
        db,
        user.id,
        account_id,
        payload,
    )

    return account_service.with_balances(db, [account])[0]


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_account(
    account_id: int,
    user: CurrentUser,
    db: DbSession,
):
    account_service.delete_account(
        db,
        user.id,
        account_id,
    )


# ============================================================
# PERMANENT USER ACCOUNT DELETION
# ============================================================

@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_account(
    payload: AccountDeleteRequest,
    user: CurrentUser,
    db: DbSession,
):
    account_service.delete_user_account(
        db,
        user,
        payload.value,
    )


@router.get("/categories")
def list_categories(
    user: CurrentUser,
    db: DbSession,
    kind: CategoryKind | None = None,
):
    categories = category_service.list_categories(
        db,
        user.id,
        kind,
    )

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "kind": (
                    c.kind.value
                    if hasattr(c.kind, "value")
                    else str(c.kind)
                ),
                "color": c.color,
            }
            for c in categories
        ]
    }