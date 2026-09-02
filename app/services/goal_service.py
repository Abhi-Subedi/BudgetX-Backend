from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Notification, SavingsGoal
from app.schemas import ContributionIn, GoalCreate, GoalUpdate
from app.services.common import get_owned


def list_goals(db: Session, user_id: int) -> list[SavingsGoal]:
    stmt = select(SavingsGoal).where(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at.desc())
    return list(db.scalars(stmt).all())


def get_goal(db: Session, user_id: int, goal_id: int) -> SavingsGoal:
    return get_owned(db, SavingsGoal, goal_id, user_id, "Goal")


def create_goal(db: Session, user_id: int, data: GoalCreate) -> SavingsGoal:
    goal = SavingsGoal(
        user_id=user_id,
        name=data.name,
        target_amount=data.target_amount,
        deadline=data.deadline,
        color=data.color if data.color.startswith("#") else "#0C5B45",
        group_id=data.group_id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, user_id: int, goal_id: int, data: GoalUpdate) -> SavingsGoal:
    goal = get_goal(db, user_id, goal_id)
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user_id: int, goal_id: int) -> None:
    goal = get_goal(db, user_id, goal_id)
    db.delete(goal)
    db.commit()


def contribute(db: Session, user_id: int, goal_id: int, data: ContributionIn) -> SavingsGoal:
    goal = get_goal(db, user_id, goal_id)
    goal.current_amount = round(float(goal.current_amount or 0) + data.amount, 2)
    reached_before = float(goal.current_amount - data.amount) >= float(goal.target_amount)
    db.commit()
    db.refresh(goal)

    if not reached_before and goal.current_amount >= goal.target_amount:
        db.add(
            Notification(
                user_id=user_id,
                type="goal",
                title=f"Goal reached: {goal.name}",
                body="You've fully funded this goal. Time to celebrate.",
            )
        )
        db.commit()
    return goal
