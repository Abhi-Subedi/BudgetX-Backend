from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import ContributionIn, GoalCreate, GoalUpdate
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


def _goal_dict(goal) -> dict:
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": round(float(goal.target_amount), 2),
        "current_amount": round(float(goal.current_amount), 2),
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "color": goal.color,
        "group_id": goal.group_id,
    }


@router.get("")
def list_goals(user: CurrentUser, db: DbSession):
    return {"items": [_goal_dict(g) for g in goal_service.list_goals(db, user.id)]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, user: CurrentUser, db: DbSession):
    return _goal_dict(goal_service.create_goal(db, user.id, payload))


@router.put("/{goal_id}")
def update_goal(goal_id: int, payload: GoalUpdate, user: CurrentUser, db: DbSession):
    return _goal_dict(goal_service.update_goal(db, user.id, goal_id, payload))


@router.post("/{goal_id}/contributions")
def contribute(goal_id: int, payload: ContributionIn, user: CurrentUser, db: DbSession):
    return _goal_dict(goal_service.contribute(db, user.id, goal_id, payload))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, user: CurrentUser, db: DbSession):
    goal_service.delete_goal(db, user.id, goal_id)
