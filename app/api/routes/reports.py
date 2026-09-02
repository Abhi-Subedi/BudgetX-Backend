from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.get("/reports/monthly")
def monthly_report(
    user: CurrentUser,
    db: DbSession,
    year: int = Query(default=date.today().year, ge=2000, le=2200),
    month: int = Query(default=date.today().month, ge=1, le=12),
):
    return report_service.generate_monthly_report(db, user.id, year, month)
