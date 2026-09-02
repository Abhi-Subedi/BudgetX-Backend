from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class NotificationPreferences(TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    budget_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    overspending_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bill_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    goal_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weekly_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    monthly_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    security_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="notification_preferences")
