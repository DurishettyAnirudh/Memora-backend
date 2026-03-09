"""Calendar schemas."""

from datetime import datetime, date

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: int
    title: str
    start: datetime
    end: datetime | None = None
    domain_id: int | None = None
    domain_name: str | None = None
    domain_color: str | None = None
    priority: str = "medium"
    status: str = "pending"
    is_flexible: bool = False
    is_recurring: bool = False
    duration_minutes: int | None = None
    has_conflict: bool = False


class CalendarFilters(BaseModel):
    start: date
    end: date
    domains: list[int] | None = None
    view: str = "week"


class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int


class DayLoad(BaseModel):
    date: date
    task_count: int
    total_hours: float
