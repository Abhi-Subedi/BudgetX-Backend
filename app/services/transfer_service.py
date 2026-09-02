from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Account, Transaction, TransactionType
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate
from app.services.common import get_owned


def _verify_account(db: Session, user_id: int, account_id: int) -> Account:
    return get_owned(db, Account, account_id, user_id, "Account")


def create_transfer(db: Session, user_id: int, data: TransferCreate) -> Transfer:
    from_account = _verify_account(db, user_id, data.from_account_id)
    to_account = _verify_account(db, user_id, data.to_account_id)

    if data.from_account_id == data.to_account_id:
        raise AppError(400, "Cannot transfer to the same account.")

    transfer = Transfer(
        user_id=user_id,
        from_account_id=data.from_account_id,
        to_account_id=data.to_account_id,
        amount=data.amount,
        fee=data.fee,
        note=data.note,
    )
    db.add(transfer)

    debit_amount = data.amount + data.fee
    db.add(
        Transaction(
            user_id=user_id,
            account_id=data.from_account_id,
            category_id=None,
            type=TransactionType.expense,
            amount=debit_amount,
            occurred_at=date.today(),
            payee=f"Transfer to {to_account.name}",
            note=data.note,
        )
    )

    db.add(
        Transaction(
            user_id=user_id,
            account_id=data.to_account_id,
            category_id=None,
            type=TransactionType.income,
            amount=data.amount,
            occurred_at=date.today(),
            payee=f"Transfer from {from_account.name}",
            note=data.note,
        )
    )

    if data.fee > 0:
        db.add(
            Transaction(
                user_id=user_id,
                account_id=data.from_account_id,
                category_id=None,
                type=TransactionType.expense,
                amount=data.fee,
                occurred_at=date.today(),
                payee="Transfer Fee",
                note=f"Fee for transfer of {data.amount}",
            )
        )

    db.commit()
    db.refresh(transfer)
    return transfer


def list_transfers(
    db: Session, user_id: int, *, page: int, page_size: int
) -> tuple[list[Transfer], int]:
    stmt = select(Transfer).where(Transfer.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(Transfer.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, int(total)


def get_transfer(db: Session, user_id: int, transfer_id: int) -> Transfer:
    return get_owned(db, Transfer, transfer_id, user_id, "Transfer")


def delete_transfer(db: Session, user_id: int, transfer_id: int) -> None:
    transfer = get_owned(db, Transfer, transfer_id, user_id, "Transfer")
    db.delete(transfer)
    db.commit()
