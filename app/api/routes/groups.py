from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import GroupCreate, GroupExpenseIn, InviteIn, JoinIn, RoleUpdateIn
from app.services import group_finance_service, group_service

router = APIRouter(prefix="/groups", tags=["groups"])


def _group_dict(db, group) -> dict:
    members = group_service.members_of(db, group.id)
    return {
        "id": group.id,
        "name": group.name,
        "currency": group.currency,
        "invite_code": group.invite_code,
        "owner_id": group.owner_id,
        "member_count": len(members),
    }


@router.get("")
def list_groups(user: CurrentUser, db: DbSession):
    groups = group_service.list_groups(db, user.id)
    return {"items": [_group_dict(db, g) for g in groups]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, user: CurrentUser, db: DbSession):
    group = group_service.create_group(db, user.id, payload.name, payload.currency)
    return _group_dict(db, group)


@router.get("/{group_id}")
def get_group(group_id: int, user: CurrentUser, db: DbSession):
    group, membership = group_service.get_group_for_member(db, group_id, user.id)
    data = _group_dict(db, group)
    data["invite_code"] = group.invite_code
    data["your_role"] = membership.role.value if hasattr(membership.role, "value") else str(membership.role)
    data["members"] = [
        {"user_id": m.user_id, "name": name, "email": email, "role": m.role.value if hasattr(m.role, "value") else str(m.role)}
        for m, name, email in group_service.members_of(db, group.id)
    ]
    return data


@router.post("/{group_id}/invite", status_code=status.HTTP_201_CREATED)
def invite(group_id: int, payload: InviteIn, user: CurrentUser, db: DbSession):
    group, membership = group_service.get_group_for_member(db, group_id, user.id)
    from app.models.enums import GroupRole

    group_service.require_role(membership, GroupRole.owner, GroupRole.admin)
    invitation = group_service.invite(db, group, user.id, payload.email)
    return {"code": invitation.code, "email": invitation.email}


@router.post("/join")
def join(payload: JoinIn, user: CurrentUser, db: DbSession):
    group = group_service.accept_invitation(db, user.id, payload.code.strip())
    return {"id": group.id, "name": group.name}


@router.patch("/{group_id}/members/{user_id}/role")
def update_role(group_id: int, user_id: int, payload: RoleUpdateIn, user: CurrentUser, db: DbSession):
    from app.models.enums import GroupRole

    group, actor_membership = group_service.get_group_for_member(db, group_id, user.id)
    updated = group_service.update_role(db, actor_membership, group.id, user_id, GroupRole(payload.role))
    return {"user_id": updated.user_id, "role": updated.role.value}


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(group_id: int, user_id: int, user: CurrentUser, db: DbSession):
    group, actor_membership = group_service.get_group_for_member(db, group_id, user.id)
    if user_id == user.id:
        group_service.leave_group(db, group, user.id)
    else:
        group_service.remove_member(db, actor_membership, group, user_id)


@router.post("/{group_id}/expenses", status_code=status.HTTP_201_CREATED)
def add_expense(group_id: int, payload: GroupExpenseIn, user: CurrentUser, db: DbSession):
    txn = group_finance_service.add_group_expense(db, group_id=group_id, actor_id=user.id, data=payload)
    return {"transaction_id": txn.id}


@router.get("/{group_id}/balances")
def balances(group_id: int, user: CurrentUser, db: DbSession):
    group_service.get_group_for_member(db, group_id, user.id)
    return {"items": group_finance_service.group_balances(db, group_id)}


@router.get("/{group_id}/activity")
def activity(group_id: int, user: CurrentUser, db: DbSession):
    group_service.get_group_for_member(db, group_id, user.id)
    return {"items": group_finance_service.group_activity(db, group_id, user.id)}
