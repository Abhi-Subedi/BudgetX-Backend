from datetime import date, datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from app.models.enums import DebtStatus, DebtType


class DebtBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(min_length=1, max_length=120)
    # Accepts both "type" (frontend JSON) and "debt_type" (database column name)
    type: DebtType = Field(
        default=DebtType.other,
        validation_alias=AliasChoices("type", "debt_type"),
        serialization_alias="type",
    )
    principal: float = Field(ge=0)
    remaining_balance: float | None = Field(default=None, ge=0)
    interest_rate: float = Field(ge=0, le=100, default=0)
    minimum_payment: float = Field(ge=0, default=0)
    due_day: int = Field(ge=1, le=31, default=1)
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    status: DebtStatus = DebtStatus.active

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Debt name cannot be empty")
        return v

    @field_validator("principal", "minimum_payment")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("remaining_balance")
    @classmethod
    def round_remaining(cls, v: float | None) -> float | None:
        return round(v, 2) if v is not None else None

    @field_validator("interest_rate")
    @classmethod
    def round_rate(cls, v: float) -> float:
        return round(v, 2)


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: DebtType | None = Field(
        default=None,
        validation_alias=AliasChoices("type", "debt_type"),
    )
    interest_rate: float | None = Field(default=None, ge=0, le=100)
    minimum_payment: float | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)
    remaining_balance: float | None = Field(default=None, ge=0)
    end_date: date | None = None
    status: DebtStatus | None = None


class DebtRead(DebtBase):
    id: int
    user_id: int
    remaining_balance: float
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def paid_off(self) -> bool:
        return self.remaining_balance <= 0 or self.status == DebtStatus.paid_off


class DebtPaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_date: date = Field(default_factory=date.today)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)


class DebtPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debt_id: int
    amount: float
    payment_date: date
    note: str | None
    created_at: datetime


class DebtSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_debt: float
    total_paid: float = 0.0
    total_remaining: float = 0.0
    active_debts: int = Field(
        default=0,
        validation_alias=AliasChoices("active_debts", "active_count"),
        serialization_alias="active_count",
    )
    monthly_payments: float
    debts: list[DebtRead] = Field(default_factory=list)

    @computed_field
    @property
    def active_count(self) -> int:
        return self.active_debts