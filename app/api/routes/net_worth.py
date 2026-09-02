from datetime import date

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.net_worth import NetWorthCurrent, NetWorthHistory, NetWorthSnapshotRead
from app.services import net_worth_service

router = APIRouter(tags=["net worth"])


@router.post("/net-worth/snapshot", status_code=status.HTTP_201_CREATED)
def create_snapshot(user: CurrentUser, db: DbSession) -> NetWorthSnapshotRead:
    snapshot = net_worth_service.save_snapshot(db, user.id)
    return snapshot


@router.get("/net-worth/history")
def get_history(
    user: CurrentUser,
    db: DbSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> NetWorthHistory:
    snapshots = net_worth_service.get_history(db, user.id, start_date, end_date)
    return NetWorthHistory(items=snapshots, count=len(snapshots))


@router.get("/net-worth/current")
def get_current(user: CurrentUser, db: DbSession) -> NetWorthCurrent:
    data = net_worth_service.calculate_net_worth(db, user.id)
    return data
