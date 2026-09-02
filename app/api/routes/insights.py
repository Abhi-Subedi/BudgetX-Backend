from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import analytics_service, dashboard_service

router = APIRouter(tags=["insights"])


@router.get("/dashboard")
def dashboard(user: CurrentUser, db: DbSession):
    return dashboard_service.build_dashboard(db, user)


@router.get("/analytics/overview")
def analytics_overview(user: CurrentUser, db: DbSession, month: str = Query(default=None)):
    from datetime import date

    month_key = month or f"{date.today().year}-{date.today().month:02d}"
    return analytics_service.overview(db, user.id, month_key)


@router.get("/analytics/trends")
def analytics_trends(
    user: CurrentUser,
    db: DbSession,
    months: int = Query(default=6, ge=3, le=24),
    end_month: str = Query(default=None),
):
    from datetime import date

    month_key = end_month or f"{date.today().year}-{date.today().month:02d}"
    return {"items": analytics_service.trends(db, user.id, month_key, months)}
