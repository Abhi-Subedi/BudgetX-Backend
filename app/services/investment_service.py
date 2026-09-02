from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Account, Investment
from app.schemas.investment import AllocationSlice, InvestmentCreate, InvestmentUpdate, PortfolioSummary
from app.services.common import get_owned


def list_investments(db: Session, user_id: int) -> list[Investment]:
    stmt = select(Investment).where(Investment.user_id == user_id).order_by(Investment.created_at.desc())
    return list(db.scalars(stmt).all())


def create_investment(db: Session, user_id: int, data: InvestmentCreate) -> Investment:
    get_owned(db, Account, data.account_id, user_id, "Account")
    investment = Investment(
        user_id=user_id,
        account_id=data.account_id,
        name=data.name,
        investment_type=data.investment_type,
        symbol=data.symbol,
        units=data.units,
        buy_price=data.buy_price,
        current_price=data.current_price,
        buy_date=data.buy_date,
        notes=data.notes,
    )
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


def get_investment(db: Session, user_id: int, investment_id: int) -> Investment:
    return get_owned(db, Investment, investment_id, user_id, "Investment")


def update_investment(db: Session, user_id: int, investment_id: int, data: InvestmentUpdate) -> Investment:
    investment = get_investment(db, user_id, investment_id)
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(investment, field, value)
    db.commit()
    db.refresh(investment)
    return investment


def delete_investment(db: Session, user_id: int, investment_id: int) -> None:
    investment = get_investment(db, user_id, investment_id)
    db.delete(investment)
    db.commit()


def update_current_price(db: Session, user_id: int, investment_id: int, price: float) -> Investment:
    investment = get_investment(db, user_id, investment_id)
    investment.current_price = round(price, 2)
    db.commit()
    db.refresh(investment)
    return investment


def _calc_invested(inv: Investment) -> float:
    return round(float(inv.units) * float(inv.buy_price), 2)


def _calc_current_value(inv: Investment) -> float:
    return round(float(inv.units) * float(inv.current_price), 2)


def get_portfolio_summary(db: Session, user_id: int) -> PortfolioSummary:
    investments = list_investments(db, user_id)

    total_invested = 0.0
    current_value = 0.0
    by_type: dict[str, dict] = {}

    for inv in investments:
        invested = _calc_invested(inv)
        value = _calc_current_value(inv)
        total_invested += invested
        current_value += value

        type_key = inv.investment_type.value if hasattr(inv.investment_type, "value") else str(inv.investment_type)
        if type_key not in by_type:
            by_type[type_key] = {"invested": 0.0, "current_value": 0.0, "count": 0}
        by_type[type_key]["invested"] += invested
        by_type[type_key]["current_value"] += value
        by_type[type_key]["count"] += 1

    total_invested = round(total_invested, 2)
    current_value = round(current_value, 2)
    profit_loss = round(current_value - total_invested, 2)
    roi_pct = round(profit_loss / total_invested * 100, 2) if total_invested > 0 else 0.0

    allocation = []
    for type_key, data in by_type.items():
        inv = round(data["invested"], 2)
        val = round(data["current_value"], 2)
        pl = round(val - inv, 2)
        roi = round(pl / inv * 100, 2) if inv > 0 else 0.0
        pct = round(val / current_value * 100, 2) if current_value > 0 else 0.0
        allocation.append(
            AllocationSlice(
                investment_type=type_key,
                invested=inv,
                current_value=val,
                profit_loss=pl,
                roi_pct=roi,
                pct=pct,
                count=data["count"],
            )
        )
    allocation.sort(key=lambda a: a.current_value, reverse=True)

    return PortfolioSummary(
        total_invested=total_invested,
        current_value=current_value,
        profit_loss=profit_loss,
        roi_pct=roi_pct,
        investment_count=len(investments),
        allocation=allocation,
    )


def get_investment_history(db: Session, user_id: int) -> list[dict]:
    investments = list_investments(db, user_id)
    history = []
    for inv in investments:
        invested = _calc_invested(inv)
        value = _calc_current_value(inv)
        history.append(
            {
                "id": inv.id,
                "account_id": inv.account_id,
                "name": inv.name,
                "investment_type": inv.investment_type.value if hasattr(inv.investment_type, "value") else str(inv.investment_type),
                "symbol": inv.symbol,
                "units": float(inv.units),
                "buy_price": float(inv.buy_price),
                "current_price": float(inv.current_price),
                "invested": invested,
                "current_value": value,
                "profit_loss": round(value - invested, 2),
                "roi_pct": round((value - invested) / invested * 100, 2) if invested > 0 else 0.0,
                "buy_date": inv.buy_date.isoformat(),
                "notes": inv.notes,
                "created_at": inv.created_at.isoformat(),
                "updated_at": inv.updated_at.isoformat(),
            }
        )
    return history
