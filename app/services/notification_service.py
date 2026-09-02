from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification


def list_notifications(db: Session, user_id: int, limit: int = 50) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def unread_count(db: Session, user_id: int) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
        or 0
    )


def mark_all_read(db: Session, user_id: int) -> None:
    db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read.is_(False)).update(
        {"is_read": True}
    )
    db.commit()
