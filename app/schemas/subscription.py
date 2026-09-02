from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models.enums import SubscriptionFrequency


def _round2(v: float) -> float:
    return round(float(v), 2)


class SubscriptionCreate(BaseModel):
    name: str = Field(max_length=160)
    amount: float = Field(gt=0)
    frequency: SubscriptionFrequency
    category: str | None = Field(default=None, max_length=100)
    next_billing_date: date
    start_date: date
    end_date: date | None = None
    account_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    amount: float | None = Field(default=None, gt=0)
    frequency: SubscriptionFrequency | None = None
    category: str | None = Field(default=None, max_length=100)
    next_billing_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    account_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v


class SubscriptionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    amount: float
    frequency: SubscriptionFrequency
    category: str | None
    next_billing_date: date
    start_date: date
    end_date: date | None
    is_active: bool
    account_id: int | None
    notes: str | None
    logo_url: str | None
    created_at: date
    updated_at: date

    @field_validator("amount", mode="before")
    @classmethod
    def round_amount(cls, v) -> float:
        return _round2(float(v))


class SubscriptionSummary(BaseModel):
    monthly_cost: float
    annual_cost: float
    total_count: int
    active_count: int

    @field_validator("monthly_cost", "annual_cost", mode="before")
    @classmethod
    def round_values(cls, v) -> float:
        return _round2(float(v))
