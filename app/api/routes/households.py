from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.services import household_service

router = APIRouter(prefix="/households", tags=["households"])


class CreateHouseholdIn(BaseModel):
    name: str


class JoinHouseholdIn(BaseModel):
    invite_code: str


class UpdateRoleIn(BaseModel):
    role: str


def _household_dict(db, household, membership=None) -> dict:
    members = household_service.get_household_members(db, household.id)
    result = {
        "id": household.id,
        "name": household.name,
        "invite_code": household.invite_code,
        "created_by": household.created_by,
        "member_count": len(members),
        "created_at": household.created_at,
        "updated_at": household.updated_at,
    }
    if membership is not None:
        result["your_role"] = membership.role
    return result


@router.get("", status_code=status.HTTP_200_OK)
def list_households(user: CurrentUser, db: DbSession):
    households = household_service.get_user_households(db, user.id)
    return {"items": [_household_dict(db, h) for h in households]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_household(payload: CreateHouseholdIn, user: CurrentUser, db: DbSession):
    if not payload.name.strip():
        raise AppError(400, "Household name cannot be empty.")
    household = household_service.create_household(db, user.id, payload.name)
    return _household_dict(db, household)


@router.get("/{household_id}", status_code=status.HTTP_200_OK)
def get_household(household_id: int, user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.household import Household as HouseholdModel, HouseholdMember

    household = db.get(HouseholdModel, household_id)
    if household is None:
        raise AppError(404, "Household not found.")
    membership = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user.id,
        )
    )
    if membership is None:
        raise AppError(403, "You are not a member of this household.")
    data = _household_dict(db, household, membership)
    data["members"] = [
        {"user_id": m.user_id, "role": m.role, "joined_at": m.joined_at}
        for m in household_service.get_household_members(db, household_id)
    ]
    return data


@router.post("/join", status_code=status.HTTP_200_OK)
def join_household(payload: JoinHouseholdIn, user: CurrentUser, db: DbSession):
    household = household_service.join_household(db, user.id, payload.invite_code)
    return {"id": household.id, "name": household.name}


@router.delete("/{household_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(household_id: int, user_id: int, user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.household import HouseholdMember

    actor = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user.id,
        )
    )
    if actor is None or actor.role not in ("owner", "admin"):
        if user_id != user.id:
            raise AppError(403, "Only owners and admins can remove members.")
    if user_id == user.id:
        household_service.leave_household(db, user.id, household_id)
    else:
        household_service.remove_member(db, household_id, user_id)


@router.patch("/{household_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def update_member_role(household_id: int, user_id: int, payload: UpdateRoleIn, user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.household import HouseholdMember

    actor = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user.id,
        )
    )
    if actor is None or actor.role != "owner":
        raise AppError(403, "Only the household owner can change member roles.")
    updated = household_service.update_member_role(db, household_id, user_id, payload.role)
    return {"user_id": updated.user_id, "role": updated.role}
