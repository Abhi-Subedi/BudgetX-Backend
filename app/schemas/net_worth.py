from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class NetWorthSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_assets: float
    total_liabilities: float
    net_worth: float
    snapshot_date: date
    created_at: datetime


class NetWorthHistory(BaseModel):
    items: list[NetWorthSnapshotRead]
    count: int


class NetWorthCurrent(BaseModel):
    total_assets: float
    total_liabilities: float
    net_worth: float
    as_of: date
