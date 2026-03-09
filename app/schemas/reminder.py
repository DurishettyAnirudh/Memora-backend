"""Reminder schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReminderCreate(BaseModel):
    task_id: int
    reminder_type: Literal["point", "lead_time", "day_before", "recurring", "contextual"] = (
        "lead_time"
    )
    trigger_at: datetime
    is_recurring: bool = False
    recurrence_rule: str | None = None


class ReminderResponse(BaseModel):
    id: int
    task_id: int
    reminder_type: str
    trigger_at: datetime
    is_recurring: bool
    recurrence_rule: str | None = None
    is_fired: bool
    is_dismissed: bool
    snoozed_until: datetime | None = None
    notification_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SnoozeRequest(BaseModel):
    duration: Literal["5m", "15m", "1h"]
