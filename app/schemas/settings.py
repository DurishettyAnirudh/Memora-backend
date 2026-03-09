"""Settings schemas."""

from datetime import datetime

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    work_start_hour: int
    work_end_hour: int
    work_days: str
    default_duration_minutes: int
    default_reminder_lead_minutes: int
    daily_task_limit_hours: float
    buffer_minutes: int
    weekend_mode: bool
    theme: str
    selected_model: str
    nudge_preferences: str
    auto_backup_enabled: bool
    auto_backup_interval_days: int
    auto_backup_path: str | None = None
    telegram_chat_id: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    work_start_hour: int | None = None
    work_end_hour: int | None = None
    work_days: str | None = None
    default_duration_minutes: int | None = None
    default_reminder_lead_minutes: int | None = None
    daily_task_limit_hours: float | None = None
    buffer_minutes: int | None = None
    weekend_mode: bool | None = None
    theme: str | None = None
    selected_model: str | None = None
    nudge_preferences: str | None = None
    auto_backup_enabled: bool | None = None
    auto_backup_interval_days: int | None = None
    auto_backup_path: str | None = None
    telegram_chat_id: str | None = None
