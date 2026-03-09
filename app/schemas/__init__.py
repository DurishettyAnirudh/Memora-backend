"""Pydantic request/response schemas."""

from app.schemas.domain import DomainCreate, DomainUpdate, DomainResponse
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    BulkOperation,
    BulkResult,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetail,
    MilestoneCreate,
    MilestoneResponse,
)
from app.schemas.reminder import ReminderCreate, ReminderResponse, SnoozeRequest
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage, SystemEvent, LiveContext
from app.schemas.calendar import CalendarEvent, CalendarFilters, TimeSlot, DayLoad
from app.schemas.memory import MemoryFact, MemoryGroup, MemoryUpdate
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.schemas.common import (
    PaginationParams,
    ErrorResponse,
    SuccessResponse,
    SearchResult,
    ImportResult,
    BackupRecord,
)

__all__ = [
    "DomainCreate", "DomainUpdate", "DomainResponse",
    "TaskCreate", "TaskUpdate", "TaskResponse", "BulkOperation", "BulkResult",
    "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectDetail",
    "MilestoneCreate", "MilestoneResponse",
    "ReminderCreate", "ReminderResponse", "SnoozeRequest",
    "ChatRequest", "ChatResponse", "ChatMessage", "SystemEvent", "LiveContext",
    "CalendarEvent", "CalendarFilters", "TimeSlot", "DayLoad",
    "MemoryFact", "MemoryGroup", "MemoryUpdate",
    "SettingsResponse", "SettingsUpdate",
    "PaginationParams", "ErrorResponse", "SuccessResponse",
    "SearchResult", "ImportResult", "BackupRecord",
]
