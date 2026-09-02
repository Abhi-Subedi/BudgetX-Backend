from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Transaction, User


def get_admin_stats(db: Session) -> dict:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = db.scalar(
        select(func.count()).select_from(User).where(User.updated_at >= thirty_days_ago)
    ) or 0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_registrations = db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= month_start)
    ) or 0

    total_transactions = db.scalar(select(func.count()).select_from(Transaction)) or 0
    total_accounts = db.scalar(select(func.count()).select_from(Account)) or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_registrations_this_month": new_registrations,
        "total_transactions": total_transactions,
        "total_accounts": total_accounts,
    }
