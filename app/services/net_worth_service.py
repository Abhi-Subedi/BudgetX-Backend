from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, NetWorthSnapshot
from app.services.common import account_balance


def calculate_net_worth(db: Session, user_id: int) -> dict:
    accounts = db.scalars(
        select(Account).where(Account.user_id == user_id, Account.archived.is_(False))
    ).all()
    total_assets = round(sum(account_balance(db, a) for a in accounts), 2)
    total_liabilities = 0.0
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": round(total_assets - total_liabilities, 2),
        "as_of": date.today(),
    }


def save_snapshot(db: Session, user_id: int) -> NetWorthSnapshot:
    data = calculate_net_worth(db, user_id)
    snapshot = NetWorthSnapshot(
        user_id=user_id,
        total_assets=data["total_assets"],
        total_liabilities=data["total_liabilities"],
        net_worth=data["net_worth"],
        snapshot_date=data["as_of"],
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_history(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[NetWorthSnapshot]:
    stmt = select(NetWorthSnapshot).where(NetWorthSnapshot.user_id == user_id)
    if start_date is not None:
        stmt = stmt.where(NetWorthSnapshot.snapshot_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(NetWorthSnapshot.snapshot_date <= end_date)
    return list(db.scalars(stmt.order_by(NetWorthSnapshot.snapshot_date)).all())
