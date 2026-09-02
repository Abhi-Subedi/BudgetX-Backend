from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Transaction
from app.models.tag import Tag, transaction_tags
from app.schemas.tag import TagCreate
from app.services.common import get_owned


def create_tag(db: Session, user_id: int, data: TagCreate) -> Tag:
    exists = db.scalar(
        select(Tag).where(Tag.user_id == user_id, Tag.name == data.name.strip())
    )
    if exists:
        raise AppError(409, "A tag with this name already exists.")
    tag = Tag(user_id=user_id, name=data.name.strip(), color=data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def list_tags(db: Session, user_id: int) -> list[Tag]:
    return list(
        db.scalars(
            select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
        ).all()
    )


def get_tag(db: Session, user_id: int, tag_id: int) -> Tag:
    return get_owned(db, Tag, tag_id, user_id, "Tag")


def delete_tag(db: Session, user_id: int, tag_id: int) -> None:
    tag = get_owned(db, Tag, tag_id, user_id, "Tag")
    db.delete(tag)
    db.commit()


def assign_tag(db: Session, user_id: int, transaction_id: int, tag_id: int) -> None:
    txn = get_owned(db, Transaction, transaction_id, user_id, "Transaction")
    tag = get_owned(db, Tag, tag_id, user_id, "Tag")
    already = db.scalar(
        select(func.count())
        .select_from(transaction_tags)
        .where(
            transaction_tags.c.transaction_id == txn.id,
            transaction_tags.c.tag_id == tag.id,
        )
    )
    if already:
        return
    db.execute(transaction_tags.insert().values(transaction_id=txn.id, tag_id=tag.id))
    db.commit()


def remove_tag(db: Session, user_id: int, transaction_id: int, tag_id: int) -> None:
    get_owned(db, Transaction, transaction_id, user_id, "Transaction")
    get_owned(db, Tag, tag_id, user_id, "Tag")
    db.execute(
        transaction_tags.delete().where(
            transaction_tags.c.transaction_id == transaction_id,
            transaction_tags.c.tag_id == tag_id,
        )
    )
    db.commit()
