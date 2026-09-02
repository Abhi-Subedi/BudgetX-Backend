from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.investment import InvestmentCreate, InvestmentUpdate
from app.services import investment_service

router = APIRouter(tags=["investments"])


@router.get("/investments")
def list_investments(user: CurrentUser, db: DbSession):
    return {"items": investment_service.get_investment_history(db, user.id)}


@router.get("/investments/portfolio")
def get_portfolio(user: CurrentUser, db: DbSession):
    return investment_service.get_portfolio_summary(db, user.id).model_dump()


@router.get("/investments/portfolio/allocation")
def get_portfolio_allocation(user: CurrentUser, db: DbSession):
    summary = investment_service.get_portfolio_summary(db, user.id)
    return {
        "total_invested": summary.total_invested,
        "current_value": summary.current_value,
        "allocation": [a.model_dump() for a in summary.allocation],
    }


@router.post("/investments", status_code=status.HTTP_201_CREATED)
def create_investment(payload: InvestmentCreate, user: CurrentUser, db: DbSession):
    investment = investment_service.create_investment(db, user.id, payload)
    return investment_service.get_investment_history(db, user.id)[0]


@router.get("/investments/{investment_id}")
def get_investment(investment_id: int, user: CurrentUser, db: DbSession):
    investment = investment_service.get_investment(db, user.id, investment_id)
    return investment_service.get_investment_history(db, user.id)[0]


@router.patch("/investments/{investment_id}")
def update_investment(investment_id: int, payload: InvestmentUpdate, user: CurrentUser, db: DbSession):
    investment = investment_service.update_investment(db, user.id, investment_id, payload)
    return investment_service.get_investment_history(db, user.id)[0]


@router.delete("/investments/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(investment_id: int, user: CurrentUser, db: DbSession):
    investment_service.delete_investment(db, user.id, investment_id)


@router.put("/investments/{investment_id}/price")
def update_price(investment_id: int, user: CurrentUser, db: DbSession, price: float = Query(gt=0)):
    investment = investment_service.update_current_price(db, user.id, investment_id, price)
    return investment_service.get_investment_history(db, user.id)[0]
