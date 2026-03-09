"""UserSettings model — single-row configuration table."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    work_start_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    work_end_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=17)
    work_days: Mapped[str] = mapped_column(
        String, nullable=False, default="[1,2,3,4,5]"
    )
    default_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    default_reminder_lead_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    daily_task_limit_hours: Mapped[float] = mapped_column(
        Float, nullable=False, default=8.0
    )
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    weekend_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    theme: Mapped[str] = mapped_column(String, nullable=False, default="dark")
    selected_model: Mapped[str] = mapped_column(
        String, nullable=False, default="gpt-oss-20b"
    )
    nudge_preferences: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    auto_backup_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    auto_backup_interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    auto_backup_path: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (CheckConstraint("id = 1", name="single_row_settings"),)
