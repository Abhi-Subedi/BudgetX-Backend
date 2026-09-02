from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import Account, GroupMember, Transaction, TransactionSplit, User
from app.models.enums import TransactionType
from app.schemas import GroupExpenseIn
from app.services.account_service import first_active_account
from app.services.group_service import member_record


def _equal_shares(amount_cents: int, participant_ids: list[int]) -> dict[int, float]:
    n = len(participant_ids)
    base = amount_cents // n
    remainder = amount_cents - base * n
    shares: dict[int, float] = {}
    for index, uid in enumerate(participant_ids):
        extra = 1 if index < remainder else 0
        shares[uid] = round((base + extra) / 100, 2)
    return shares


def add_group_expense(
    db: Session,
    *,
    group_id: int,
    actor_id: int,
    data: GroupExpenseIn,
) -> Transaction:
    membership = member_record(db, group_id, actor_id)
    if membership is None:
        raise AppError(404, "Group not found.")

    member_ids = {
        row[0]
        for row in db.execute(select(GroupMember.user_id).where(GroupMember.group_id == group_id)).all()
    }

    payer_id = data.paid_by_user_id or actor_id
    if payer_id not in member_ids:
        raise AppError(422, "The payer must be a member of this group.")

    participant_ids = data.split_with if data.split_with else sorted(member_ids)
    if len(participant_ids) == 0:
        raise AppError(422, "Pick at least one person to split with.")
    invalid = [uid for uid in participant_ids if uid not in member_ids]
    if invalid:
        raise AppError(422, "Everyone included in the split must be a member of this group.")
    if len(set(participant_ids)) != len(participant_ids):
        raise AppError(422, "Each person can only be included once in the split.")

    account_id = data.account_id
    if account_id is None:
        payer_account = first_active_account(db, payer_id)
        if payer_account is None:
            raise AppError(400, "The payer needs at least one account before recording shared expenses.")
        account_id = payer_account.id
    else:
        account = db.get(Account, account_id)
        if account is None or account.user_id != payer_id:
            raise AppError(422, "The selected account must belong to the payer.")

    if data.category_id is not None:
        from app.models import Category

        category = db.get(Category, data.category_id)
        if category is None or category.user_id != payer_id:
            raise AppError(404, "Category not found.")

    amount_cents = int(round(data.amount * 100))
    shares = _equal_shares(amount_cents, participant_ids)

    txn = Transaction(
        user_id=payer_id,
        created_by_id=actor_id,
        account_id=account_id,
        category_id=data.category_id,
        type=TransactionType.expense,
        amount=data.amount,
        occurred_at=data.occurred_at,
        payee=data.description,
        note=None,
        group_id=group_id,
    )
    db.add(txn)
    db.flush()
    for uid, share in shares.items():
        db.add(TransactionSplit(transaction_id=txn.id, user_id=uid, share=share))
    db.commit()
    db.refresh(txn)
    return txn


def group_balances(db: Session, group_id: int) -> list[dict]:
    from sqlalchemy import func

    rows = db.execute(
        select(GroupMember.user_id, User.name)
        .join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == group_id)
    ).all()
    names = {uid: name for uid, name in rows}

    paid = dict(
        db.execute(
            select(Transaction.user_id, func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.group_id == group_id)
            .group_by(Transaction.user_id)
        ).all()
    )
    owed_rows = db.execute(
        select(TransactionSplit.user_id, func.coalesce(func.sum(TransactionSplit.share), 0))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .where(Transaction.group_id == group_id)
        .group_by(TransactionSplit.user_id)
    ).all()

    net = {uid: round(float(paid.get(uid, 0)) - float(owed), 2) for uid, owed in owed_rows}
    for uid in paid:
        net.setdefault(uid, round(float(paid[uid]), 2))
    for uid in names:
        net.setdefault(uid, 0.0)

    creditors = sorted([(uid, amt) for uid, amt in net.items() if amt > 0.004], key=lambda x: -x[1])
    debtors = sorted([(-amt, uid) for uid, amt in net.items() if amt < -0.004])

    edges = []
    di = 0
    for creditor_uid, credit in creditors:
        remaining_credit = int(round(credit * 100))
        while remaining_credit > 0 and di < len(debtors):
            debt_amount, debtor_uid = debtors[di]
            available = int(round(debt_amount * 100))
            transfer = min(remaining_credit, available)
            if transfer > 0:
                edges.append(
                    {
                        "from_user_id": debtor_uid,
                        "to_user_id": creditor_uid,
                        "amount": round(transfer / 100, 2),
                    }
                )
                remaining_credit -= transfer
                new_debt = (available - transfer) / 100
                debtors[di] = (new_debt, debtor_uid)
            if available - transfer <= 0:
                di += 1

    result = []
    for uid, name in names.items():
        result.append({"user_id": uid, "name": name, "net": round(net.get(uid, 0.0), 2), "owes": []})
    edge_map: dict[int, list] = {}
    for e in edges:
        edge_map.setdefault(e["from_user_id"], []).append(e)
    for entry in result:
        entry["owes"] = [
            {"from_user_id": e["from_user_id"], "to_user_id": e["to_user_id"], "amount": e["amount"]}
            for e in edge_map.get(entry["user_id"], [])
        ]
    return sorted(result, key=lambda r: r["name"])


def group_activity(db: Session, group_id: int, viewer_id: int, limit: int = 50) -> list[dict]:
    stmt = (
        select(Transaction)
        .options(joinedload(Transaction.splits))
        .where(Transaction.group_id == group_id)
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(limit)
    )
    txns = db.scalars(stmt).unique().all()
    items = []
    payer_cache: dict[int, str] = {}

    def payer_name(uid: int | None) -> str:
        if uid is None:
            return "Unknown"
        if uid not in payer_cache:
            user = db.get(User, uid)
            payer_cache[uid] = user.name if user else "Unknown"
        return payer_cache[uid]

    viewer_split_total = 0.0
    for t in txns:
        share_for_viewer = 0.0
        for split in t.splits:
            if split.user_id == viewer_id:
                share_for_viewer = float(split.share)
        viewer_split_total += share_for_viewer
        items.append(
            {
                "transaction_id": t.id,
                "description": t.payee or "Shared expense",
                "amount": float(t.amount),
                "occurred_at": t.occurred_at,
                "paid_by_id": t.user_id,
                "paid_by_name": payer_name(t.user_id),
                "your_share": round(share_for_viewer, 2),
            }
        )
    return items
