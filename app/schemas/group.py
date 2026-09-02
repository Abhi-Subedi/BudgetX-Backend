from datetime import date

from pydantic import BaseModel, Field, field_validator


def _round2(v: float) -> float:
    return round(float(v), 2)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Group name cannot be empty")
        return v

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class GroupOut(BaseModel):
    id: int
    name: str
    currency: str
    invite_code: str
    owner_id: int
    member_count: int = 0


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class RoleUpdateIn(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("admin", "member"):
            raise ValueError("Role must be admin or member")
        return v


class InviteIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v) < 5 or len(v) > 255:
            raise ValueError("A valid email address is required")
        return v


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class GroupExpenseIn(BaseModel):
    description: str = Field(min_length=1, max_length=160)
    amount: float = Field(gt=0)
    paid_by_user_id: int | None = None
    category_id: int | None = None
    account_id: int | None = None
    occurred_at: date
    split_with: list[int] | None = None

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)

    @field_validator("description")
    @classmethod
    def strip_desc(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description cannot be empty")
        return v


class GroupBalance(BaseModel):
    user_id: int
    name: str
    net: float
    owes: list["DebtEdge"] = []


class DebtEdge(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: float


class GroupActivityItem(BaseModel):
    transaction_id: int
    description: str
    amount: float
    occurred_at: date
    paid_by_id: int
    paid_by_name: str
    your_share: float
