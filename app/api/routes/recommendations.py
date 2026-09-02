from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.services import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations")
def recommendations(user: CurrentUser, db: DbSession):
    return {"items": recommendation_service.get_recommendations(db, user.id)}
