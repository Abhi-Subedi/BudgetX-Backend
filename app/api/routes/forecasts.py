from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import forecast_service

router = APIRouter(tags=["forecasts"])


@router.get("/forecasts/balance")
def forecast_balance(user: CurrentUser, db: DbSession, days: int = Query(default=30, ge=1, le=365)):
    projection = forecast_service.project_balance(db, user.id, days)
    return projection.model_dump()


@router.get("/forecasts/spending")
def forecast_spending(user: CurrentUser, db: DbSession, months: int = Query(default=3, ge=1, le=24)):
    projection = forecast_service.project_spending(db, user.id, months)
    return projection.model_dump()


@router.get("/forecasts/warnings")
def forecast_warnings(
    user: CurrentUser,
    db: DbSession,
    threshold: float = Query(default=100.0, ge=0),
):
    warning = forecast_service.get_cash_shortage_warning(db, user.id, threshold)
    return warning.model_dump()


@router.get("/forecasts/goal-feasibility/{goal_id}")
def forecast_goal_feasibility(
    goal_id: int,
    user: CurrentUser,
    db: DbSession,
    monthly: float = Query(gt=0),
):
    result = forecast_service.get_goal_feasibility(db, user.id, goal_id, monthly)
    return result.model_dump()
