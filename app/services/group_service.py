from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Group, GroupMember, GroupRole, Invitation, InvitationStatus, Notification
from app.services.auth_service import generate_invite_code


def list_groups(db: Session, user_id: int) -> list[Group]:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def member_record(db: Session, group_id: int, user_id: int) -> GroupMember | None:
    return db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )


def get_group_for_member(db: Session, group_id: int, user_id: int) -> tuple[Group, GroupMember]:
    group = db.get(Group, group_id)
    membership = member_record(db, group_id, user_id) if group else None
    if group is None or membership is None:
        raise AppError(404, "Group not found.")
    return group, membership


def require_role(membership: GroupMember, *roles: GroupRole) -> None:
    if membership.role not in roles:
        raise AppError(403, "You don't have permission to do that in this group.")


def create_group(db: Session, owner_id: int, name: str, currency: str) -> Group:
    group = Group(name=name.strip(), owner_id=owner_id, currency=currency.upper(), invite_code=generate_invite_code(db))
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner_id, role=GroupRole.owner))
    db.commit()
    db.refresh(group)
    return group


def members_of(db: Session, group_id: int) -> list[tuple[GroupMember, str, str]]:
    from app.models import User

    rows = db.execute(
        select(GroupMember, User.name, User.email)
        .join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    ).all()
    return [(member, name, email) for member, name, email in rows]


def invite(db: Session, group: Group, inviter_id: int, email: str) -> Invitation:
    from app.models import User

    existing_member = db.execute(
        select(User.id).where(User.email == email)
    ).scalar()
    if existing_member is not None and member_record(db, group.id, existing_member) is not None:
        raise AppError(409, f"{email} is already a member of this group.")

    pending = db.scalar(
        select(Invitation).where(
            Invitation.group_id == group.id,
            Invitation.email == email,
            Invitation.status == InvitationStatus.pending,
        )
    )
    if pending is not None:
        raise AppError(409, f"An invitation for {email} is already waiting.")

    invitation = Invitation(group_id=group.id, email=email, code=generate_invite_code(db), invited_by_id=inviter_id)
    db.add(invitation)

    invitee = db.scalar(select(User).where(User.email == email))
    if invitee is not None:
        db.add(
            Notification(
                user_id=invitee.id,
                type="invitation",
                title=f"You've been invited to {group.name}",
                body=f"Use code {invitation.code} to join the group.",
            )
        )
    db.commit()
    db.refresh(invitation)
    return invitation


def accept_invitation(db: Session, user_id: int, code: str) -> Group:
    invitation = db.scalar(select(Invitation).where(Invitation.code == code))
    group_by_code = db.scalar(select(Group).where(Group.invite_code == code))

    if invitation is not None and invitation.status != InvitationStatus.pending:
        raise AppError(409, "This invitation has already been used.")

    if invitation is None and group_by_code is None:
        raise AppError(404, "That invite code isn't valid.")

    user_email = _user_email(db, user_id)
    if (
        invitation is not None
        and group_by_code is None
        and invitation.email.lower() != user_email.lower()
    ):
        raise AppError(403, "This invitation was sent to a different email address.")

    group = group_by_code or db.get(Group, invitation.group_id)
    if member_record(db, group.id, user_id) is not None:
        raise AppError(409, "You're already a member of this group.")

    db.add(GroupMember(group_id=group.id, user_id=user_id, role=GroupRole.member))
    if invitation is not None:
        invitation.status = InvitationStatus.accepted
        db.add(
            Notification(
                user_id=invitation.invited_by_id,
                type="invitation",
                title="Invitation accepted",
                body=f"{_user_email(db, user_id)} joined {group.name}.",
            )
        )
    db.commit()
    return group


def _user_email(db: Session, user_id: int) -> str:
    from app.models import User

    return db.get(User, user_id).email


def update_role(db: Session, actor_membership: GroupMember, group_id: int, target_user_id: int, new_role: GroupRole) -> GroupMember:
    require_role(actor_membership, GroupRole.owner)
    target = member_record(db, group_id, target_user_id)
    if target is None:
        raise AppError(404, "That person isn't a member of this group.")
    if target.role == GroupRole.owner:
        raise AppError(400, "The owner's role cannot be changed.")
    target.role = new_role
    db.commit()
    return target


def remove_member(db: Session, actor_membership: GroupMember, group: Group, target_user_id: int) -> None:
    require_role(actor_membership, GroupRole.owner, GroupRole.admin)
    if target_user_id == group.owner_id:
        raise AppError(400, "The group owner cannot be removed.")
    target = member_record(db, group.id, target_user_id)
    if target is None:
        raise AppError(404, "That person isn't a member of this group.")
    db.delete(target)
    db.commit()


def leave_group(db: Session, group: Group, user_id: int) -> None:
    membership = member_record(db, group.id, user_id)
    if membership is None:
        raise AppError(404, "Group not found.")
    if membership.role == GroupRole.owner:
        raise AppError(400, "Transfer ownership before leaving, or delete the group instead.")
    db.delete(membership)
    db.commit()
