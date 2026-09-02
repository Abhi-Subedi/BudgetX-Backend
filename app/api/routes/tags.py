from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.tag import TagCreate, TagOut
from app.services import tag_service

router = APIRouter(tags=["tags"])


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, user: CurrentUser, db: DbSession):
    tag = tag_service.create_tag(db, user.id, payload)
    return TagOut.model_validate(tag)


@router.get("/tags")
def list_tags(user: CurrentUser, db: DbSession):
    tags = tag_service.list_tags(db, user.id)
    return [TagOut.model_validate(t) for t in tags]


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, user: CurrentUser, db: DbSession):
    tag_service.delete_tag(db, user.id, tag_id)


@router.post("/transactions/{transaction_id}/tags", status_code=status.HTTP_201_CREATED)
def assign_tag(transaction_id: int, tag_id: int, user: CurrentUser, db: DbSession):
    tag_service.assign_tag(db, user.id, transaction_id, tag_id)
    return {"status": "ok"}


@router.delete(
    "/transactions/{transaction_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_tag(transaction_id: int, tag_id: int, user: CurrentUser, db: DbSession):
    tag_service.remove_tag(db, user.id, transaction_id, tag_id)
