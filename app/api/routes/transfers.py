from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models import Account
from app.schemas.transfer import TransferCreate, TransferList, TransferOut
from app.services import transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _to_out(db: DbSession, t) -> TransferOut:
    from_name = db.get(Account, t.from_account_id)
    to_name = db.get(Account, t.to_account_id)
    return TransferOut(
        id=t.id,
        user_id=t.user_id,
        from_account_id=t.from_account_id,
        to_account_id=t.to_account_id,
        amount=float(t.amount),
        fee=float(t.fee),
        note=t.note,
        created_at=t.created_at,
        updated_at=t.updated_at,
        from_account_name=from_name.name if from_name else None,
        to_account_name=to_name.name if to_name else None,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transfer(payload: TransferCreate, user: CurrentUser, db: DbSession):
    transfer = transfer_service.create_transfer(db, user.id, payload)
    return _to_out(db, transfer)


@router.get("")
def list_transfers(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    rows, total = transfer_service.list_transfers(db, user.id, page=page, page_size=page_size)
    return TransferList(
        items=[_to_out(db, t) for t in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{transfer_id}")
def get_transfer(transfer_id: int, user: CurrentUser, db: DbSession):
    transfer = transfer_service.get_transfer(db, user.id, transfer_id)
    return _to_out(db, transfer)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(transfer_id: int, user: CurrentUser, db: DbSession):
    transfer_service.delete_transfer(db, user.id, transfer_id)
