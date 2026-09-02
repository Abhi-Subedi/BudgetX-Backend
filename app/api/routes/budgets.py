from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import BudgetCreate, BudgetUpdate
from app.services import budget_service
from app.services.serializers import transactions_to_list

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("")
def list_budgets(user: CurrentUser, db: DbSession):
    budgets = budget_service.list_budgets(db, user.id)
    progress = budget_service.progress_for(db, user.id, budgets)
    return {"items": progress}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, user: CurrentUser, db: DbSession):
    budget_service.create_budget(db, user.id, payload)
    return {"ok": True}


@router.put("/{budget_id}")
def update_budget(budget_id: int, payload: BudgetUpdate, user: CurrentUser, db: DbSession):
    budget_service.update_budget(db, user.id, budget_id, payload)
    return {"ok": True}


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, user: CurrentUser, db: DbSession):
    budget_service.delete_budget(db, user.id, budget_id)
