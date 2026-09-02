from datetime import date

from pydantic import BaseModel, Field, field_validator


def _round2(v: float) -> float:
    return round(float(v), 2)


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: float = Field(gt=0)
    deadline: date | None = None
    color: str = Field(default="#0C5B45", max_length=9)
    group_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Goal name cannot be empty")
        return v

    @field_validator("target_amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: float | None = Field(default=None, gt=0)
    deadline: date | None = None
    color: str | None = Field(default=None, max_length=9)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("target_amount")
    @classmethod
    def round_amount(cls, v: float | None) -> float | None:
        return _round2(v) if v is not None else v


class ContributionIn(BaseModel):
    amount: float = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class GoalContribution(GoalCreate):
    current_amount: float = 0
    id: int = 0


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    deadline: date | None
    color: str
    group_id: int | None

    @field_validator("target_amount", "current_amount", mode="before")
    @classmethod
    def round_amounts(cls, v) -> float:
        return _round2(float(v))
