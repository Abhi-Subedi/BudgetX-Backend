from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import InvestmentType
from app.models.mixins import TimestampMixin


class Investment(TimestampMixin, Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    investment_type: Mapped[InvestmentType] = mapped_column(
        Enum(InvestmentType, native_enum=False), nullable=False
    )
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    units: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    buy_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    buy_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
