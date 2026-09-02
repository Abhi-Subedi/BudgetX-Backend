from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: CurrentUser, db: DbSession, unread_only: bool = False):
    items = notification_service.list_notifications(db, user.id)
    if unread_only:
        items = [n for n in items if not n.is_read]
    return {
        "items": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
        "unread": notification_service.unread_count(db, user.id),
    }


@router.post("/read-all")
def mark_all_read(user: CurrentUser, db: DbSession):
    notification_service.mark_all_read(db, user.id)
    return {"ok": True}
