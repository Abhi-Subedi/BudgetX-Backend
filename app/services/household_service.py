from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.household import Household, HouseholdMember, generate_invite_code


def create_household(db: Session, user_id: int, name: str) -> Household:
    household = Household(name=name.strip(), created_by=user_id, invite_code=generate_invite_code())
    db.add(household)
    db.flush()
    member = HouseholdMember(
        household_id=household.id,
        user_id=user_id,
        role="owner",
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(member)
    db.commit()
    db.refresh(household)
    return household


def join_household(db: Session, user_id: int, invite_code: str) -> Household:
    code = invite_code.strip().upper()
    household = db.scalar(select(Household).where(Household.invite_code == code))
    if household is None:
        raise AppError(404, "Invalid invite code.")
    existing = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id == user_id,
        )
    )
    if existing is not None:
        raise AppError(409, "You are already a member of this household.")
    member = HouseholdMember(
        household_id=household.id,
        user_id=user_id,
        role="member",
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(member)
    db.commit()
    db.refresh(household)
    return household


def leave_household(db: Session, user_id: int, household_id: int) -> None:
    member = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
        )
    )
    if member is None:
        raise AppError(404, "You are not a member of this household.")
    if member.role == "owner":
        raise AppError(400, "The owner cannot leave. Transfer ownership or delete the household.")
    db.delete(member)
    db.commit()


def get_household_members(db: Session, household_id: int) -> list[HouseholdMember]:
    return list(db.scalars(select(HouseholdMember).where(HouseholdMember.household_id == household_id)).all())


def update_member_role(db: Session, household_id: int, user_id: int, role: str) -> HouseholdMember:
    valid_roles = {"owner", "admin", "member", "viewer"}
    if role not in valid_roles:
        raise AppError(400, f"Invalid role. Must be one of: {', '.join(sorted(valid_roles))}")
    member = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
        )
    )
    if member is None:
        raise AppError(404, "User is not a member of this household.")
    member.role = role
    db.commit()
    db.refresh(member)
    return member


def get_user_households(db: Session, user_id: int) -> list[Household]:
    memberships = list(
        db.scalars(
            select(HouseholdMember).where(HouseholdMember.user_id == user_id)
        ).all()
    )
    if not memberships:
        return []
    household_ids = [m.household_id for m in memberships]
    return list(db.scalars(select(Household).where(Household.id.in_(household_ids))).all())


def remove_member(db: Session, household_id: int, target_user_id: int) -> None:
    member = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == target_user_id,
        )
    )
    if member is None:
        raise AppError(404, "User is not a member of this household.")
    if member.role == "owner":
        raise AppError(400, "Cannot remove the household owner.")
    db.delete(member)
    db.commit()
