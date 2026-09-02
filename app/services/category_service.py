from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryKind


def list_categories(db: Session, user_id: int, kind: CategoryKind | None = None) -> list[Category]:
    stmt = select(Category).where(Category.user_id == user_id)
    if kind is not None:
        stmt = stmt.where(Category.kind == kind)
    return list(db.scalars(stmt.order_by(Category.kind, Category.name)).all())
