from sqlalchemy.orm import Session

from app.models import Account, Category, Transaction


def _names(db: Session, txn: Transaction) -> tuple[str | None, str | None, str | None]:
    category_name = category_color = account_name = None
    if txn.category_id is not None:
        category = db.get(Category, txn.category_id)
        if category is not None:
            category_name = category.name
            category_color = category.color
    account = db.get(Account, txn.account_id)
    if account is not None:
        account_name = account.name
    return category_name, category_color, account_name


def transaction_to_dict(db: Session, txn: Transaction) -> dict:
    category_name, category_color, account_name = _names(db, txn)
    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "account_id": txn.account_id,
        "category_id": txn.category_id,
        "type": txn.type.value if hasattr(txn.type, "value") else str(txn.type),
        "amount": round(float(txn.amount), 2),
        "occurred_at": txn.occurred_at.isoformat(),
        "payee": txn.payee,
        "note": txn.note,
        "group_id": txn.group_id,
        "created_by_id": txn.created_by_id,
        "recurring_id": txn.recurring_id,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "splits": [{"user_id": s.user_id, "share": float(s.share)} for s in txn.splits],
        "category_name": category_name,
        "category_color": category_color,
        "account_name": account_name,
    }


def transactions_to_list(db: Session, txns) -> list[dict]:
    return [transaction_to_dict(db, t) for t in txns]
