from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import InvestmentType


def _round2(v: float) -> float:
    return round(float(v), 2)


def _round4(v: float) -> float:
    return round(float(v), 4)


class InvestmentCreate(BaseModel):
    account_id: int
    name: str = Field(min_length=1, max_length=120)
    investment_type: InvestmentType
    symbol: str | None = Field(default=None, max_length=20)
    units: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    current_price: float = Field(ge=0)
    buy_date: date
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Investment name cannot be empty")
        return v

    @field_validator("units")
    @classmethod
    def round_units(cls, v: float) -> float:
        return _round4(v)

    @field_validator("buy_price", "current_price")
    @classmethod
    def round_price(cls, v: float) -> float:
        return _round2(v)


class InvestmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    investment_type: InvestmentType | None = None
    symbol: str | None = Field(default=None, max_length=20)
    units: float | None = Field(default=None, gt=0)
    current_price: float | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("units")
    @classmethod
    def round_units(cls, v: float | None) -> float | None:
        return _round4(v) if v is not None else v

    @field_validator("current_price")
    @classmethod
    def round_price(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v


class InvestmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_id: int
    name: str
    investment_type: InvestmentType
    symbol: str | None
    units: float
    buy_price: float
    current_price: float
    buy_date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("units")
    @classmethod
    def round_units(cls, v) -> float:
        return _round4(float(v))

    @field_validator("buy_price", "current_price")
    @classmethod
    def round_price(cls, v) -> float:
        return _round2(float(v))


class AllocationSlice(BaseModel):
    investment_type: str
    invested: float
    current_value: float
    profit_loss: float
    roi_pct: float
    pct: float = 0.0
    count: int


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    profit_loss: float
    roi_pct: float
    investment_count: int
    allocation: list[AllocationSlice]
