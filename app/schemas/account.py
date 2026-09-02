from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AccountType

ACCOUNT_TYPES = ", ".join(t.value for t in AccountType)


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: AccountType = AccountType.cash
    opening_balance: float = 0
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Account name cannot be empty")
        return v

    @field_validator("opening_balance")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    archived: bool | None = None


class AccountBalance(BaseModel):
    balance: float
    income: float
    expenses: float


class AccountOut(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archived: bool
    created_at: datetime
    updated_at: datetime
    balance: float = 0

    @field_validator("balance")
    @classmethod
    def round_balance(cls, v: float) -> float:
        return round(v, 2)


def _unused(date_: date) -> None:
    return None
