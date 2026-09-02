from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#6E685C", max_length=7)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("color")
    @classmethod
    def normalize_color(cls, v: str) -> str:
        v = v.strip()
        if len(v) == 4 and v.startswith("#"):
            return "#" + v[1] * 2 + v[2] * 2 + v[3] * 2
        return v


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    color: str
    created_at: datetime
