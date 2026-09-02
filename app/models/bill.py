from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import BillFrequency, BillStatus
from app.models.mixins import TimestampMixin


class Bill(TimestampMixin, Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    frequency: Mapped[BillFrequency] = mapped_column(
        Enum(BillFrequency, native_enum=False), nullable=False
    )
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    auto_pay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, native_enum=False), default=BillStatus.pending, nullable=False
    )
