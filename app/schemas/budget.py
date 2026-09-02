from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _round2(v: float) -> float:
    return round(float(v), 2)


class BudgetItemIn(BaseModel):
    category_id: int
    amount: float = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return _round2(v)


class BudgetCreate(BaseModel):
    name: str = Field(default="Monthly budget", max_length=120)
    month: date
    items: list[BudgetItemIn] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def unique_categories(cls, items: list[BudgetItemIn]) -> list[BudgetItemIn]:
        ids = [i.category_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each category can appear only once in a budget")
        return items


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    items: list[BudgetItemIn] | None = None

    @model_validator(mode="after")
    def validate_items(self):
        if self.items is not None:
            ids = [i.category_id for i in self.items]
            if len(ids) != len(set(ids)):
                raise ValueError("Each category can appear only once in a budget")
            if not self.items:
                raise ValueError("Budget needs at least one category amount")
        return self


class BudgetItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    amount: float

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v) -> float:
        return _round2(v)


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    month: date
    created_at: object = None
    updated_at: object = None
    items: list[BudgetItemOut] = []


class BudgetProgress(BaseModel):
    id: int
    name: str
    month: date
    total_budget: float
    total_spent: float
    days_left: int
    items: list["BudgetItemProgress"]


class BudgetItemProgress(BaseModel):
    item_id: int
    category_id: int
    category_name: str
    category_color: str
    budgeted: float
    spent: float
    remaining: float
    pct_used: float
