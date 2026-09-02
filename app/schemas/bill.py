from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import BillFrequency, BillStatus


def _round2(v: float) -> float:
    return round(float(v), 2)


class BillCreate(BaseModel):
    name: str = Field(max_length=160)
    amount: float = Field(gt=0)
    category: str | None = Field(default=None, max_length=100)
    due_date: date
    frequency: BillFrequency
    account_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    reminder_days_before: int = Field(default=3, ge=0)
    auto_pay: bool = False

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class BillUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    amount: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, max_length=100)
    due_date: date | None = None
    frequency: BillFrequency | None = None
    account_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    reminder_days_before: int | None = Field(default=None, ge=0)
    auto_pay: bool | None = None
    status: BillStatus | None = None

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v


class BillRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    amount: float
    category: str | None
    due_date: date
    frequency: BillFrequency
    is_paid: bool
    paid_date: date | None
    account_id: int | None
    notes: str | None
    reminder_days_before: int
    auto_pay: bool
    status: BillStatus
    created_at: date
    updated_at: date

    @field_validator("amount", mode="before")
    @classmethod
    def round_amount(cls, v) -> float:
        return _round2(float(v))


class BillSummary(BaseModel):
    total_monthly_obligations: float
    total_pending: float
    total_paid: float
    total_overdue: float
    upcoming_count: int
    overdue_count: int

    @field_validator(
        "total_monthly_obligations",
        "total_pending",
        "total_paid",
        "total_overdue",
        mode="before",
    )
    @classmethod
    def round_values(cls, v) -> float:
        return _round2(float(v))
