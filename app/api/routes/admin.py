from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.services import admin_service

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
def admin_stats(user: CurrentUser, db: DbSession):
    if not user.is_admin:
        raise AppError(403, "Admin access required.")
    return admin_service.get_admin_stats(db)
