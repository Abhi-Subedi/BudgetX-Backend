from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, utcnow


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    total_assets: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    total_liabilities: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_worth: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
