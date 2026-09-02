from datetime import date

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import TransactionCreate, TransactionUpdate
from app.schemas.transaction import CsvTransactionRow
from app.services import transaction_service
from app.services.serializers import transactions_to_list

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    type: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    group_id: int | None = None,
    q: str | None = None,
):
    rows, total = transaction_service.list_transactions(
        db,
        user.id,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
        type_=type,
        category_id=category_id,
        account_id=account_id,
        group_id=group_id,
        q=q,
    )
    return {"items": transactions_to_list(db, rows), "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, user: CurrentUser, db: DbSession):
    txn = transaction_service.create_transaction(db, user.id, payload)
    return transactions_to_list(db, [txn])[0]


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_transactions(rows: list[CsvTransactionRow], user: CurrentUser, db: DbSession):
    created = transaction_service.import_transactions(db, user.id, rows)
    return {"created": created}


@router.get("/{transaction_id}")
def get_transaction(transaction_id: int, user: CurrentUser, db: DbSession):
    txn = transaction_service.get_transaction(db, user.id, transaction_id)
    return transactions_to_list(db, [txn])[0]


@router.put("/{transaction_id}")
def update_transaction(transaction_id: int, payload: TransactionUpdate, user: CurrentUser, db: DbSession):
    txn = transaction_service.update_transaction(db, user.id, transaction_id, payload)
    return transactions_to_list(db, [txn])[0]


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, user: CurrentUser, db: DbSession):
    transaction_service.delete_transaction(db, user.id, transaction_id)
