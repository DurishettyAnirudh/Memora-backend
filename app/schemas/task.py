"""Task schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    domain_id: int | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    duration_minutes: int | None = None
    is_flexible: bool = False
    is_recurring: bool = False
    recurrence_rule: str | None = None
    parent_task_id: int | None = None
    project_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    domain_id: int | None = None
    priority: Literal["high", "medium", "low"] | None = None
    status: Literal["pending", "in_progress", "completed", "cancelled"] | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    duration_minutes: int | None = None
    is_flexible: bool | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = None
    parent_task_id: int | None = None
    project_id: int | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    domain_id: int | None = None
    priority: str
    status: str
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    duration_minutes: int | None = None
    is_flexible: bool
    is_recurring: bool
    recurrence_rule: str | None = None
    parent_task_id: int | None = None
    project_id: int | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkOperation(BaseModel):
    operation: Literal["complete_all", "delete", "reschedule"]
    task_ids: list[int] = []
    # For reschedule
    reschedule_delta_days: int | None = None
    reschedule_to: datetime | None = None


class BulkResult(BaseModel):
    affected_count: int
    task_ids: list[int]
    errors: list[str] = []
