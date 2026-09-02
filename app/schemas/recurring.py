from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Frequency, TransactionType


def _round2(v: float) -> float:
    return round(float(v), 2)


class RecurringCreate(BaseModel):
    amount: float = Field(gt=0)
    type: TransactionType
    account_id: int
    category_id: int | None = None
    frequency: Frequency
    next_run_date: date
    end_date: date | None = None
    payee: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class RecurringUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    frequency: Frequency | None = None
    next_run_date: date | None = None
    end_date: date | None = None
    payee: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=500)
    active: bool | None = None

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v


class RecurringOut(RecurringCreate):
    model_config = {"from_attributes": True}

    id: int
    active: bool

    @field_validator("amount", mode="before")
    @classmethod
    def round_amount(cls, v) -> float:
        return _round2(float(v))
