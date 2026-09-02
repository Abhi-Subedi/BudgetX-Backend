from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TransactionType


def _round2(v: float) -> float:
    return round(float(v), 2)


class TransactionBase(BaseModel):
    amount: float = Field(gt=0)
    type: TransactionType
    account_id: int
    category_id: int | None = None
    occurred_at: date
    payee: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=500)
    group_id: int | None = None

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)

    @field_validator("payee", "note")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip() or None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    type: TransactionType | None = None
    account_id: int | None = None
    category_id: int | None = None
    occurred_at: date | None = None
    payee: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v

    @field_validator("payee", "note")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip() or None


class SplitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    share: float


class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: int | None
    recurring_id: int | None
    created_at: datetime
    splits: list[SplitOut] = []
    category_name: str | None = None
    category_color: str | None = None
    account_name: str | None = None


class Page(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class CsvTransactionRow(BaseModel):
    occurred_at: date
    type: TransactionType
    amount: float = Field(gt=0)
    account_id: int
    category_id: int | None = None
    payee: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)

    @field_validator("payee", "note")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip() or None


__all__ = ["CsvTransactionRow", "Page", "SplitOut", "TransactionCreate", "TransactionOut", "TransactionUpdate"]
