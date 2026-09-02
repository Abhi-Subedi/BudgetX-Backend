from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import audit_service

router = APIRouter(tags=["audit"])


@router.get("/audit-log")
def audit_log(
    user: CurrentUser,
    db: DbSession,
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return audit_service.get_audit_log(db, user.id, entity_type=entity_type, limit=limit, offset=offset)
