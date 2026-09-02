from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.services import health_score_service

router = APIRouter(tags=["health"])


@router.get("/health/score")
def health_score(user: CurrentUser, db: DbSession):
    return health_score_service.calculate_health_score(db, user.id)
