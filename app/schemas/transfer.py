from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _round2(v: float) -> float:
    return round(float(v), 2)


class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0)
    fee: float = Field(default=0, ge=0)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("amount", "fee")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)

    @field_validator("note")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip() or None


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    from_account_id: int
    to_account_id: int
    amount: float
    fee: float
    note: str | None
    created_at: datetime
    updated_at: datetime
    from_account_name: str | None = None
    to_account_name: str | None = None


class TransferList(BaseModel):
    items: list[TransferOut]
    total: int
    page: int
    page_size: int
