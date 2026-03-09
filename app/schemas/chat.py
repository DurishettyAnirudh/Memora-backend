"""Chat schemas."""

from typing import Any, Literal

from pydantic import BaseModel


class HistoryMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    history: list[HistoryMessage] = []
    utc_offset_minutes: int = 0  # client's UTC offset, e.g. 330 for UTC+5:30


class ConfirmRequest(BaseModel):
    session_id: str
    option_id: str


class SystemEvent(BaseModel):
    type: Literal[
        "task_created", "task_updated", "task_deleted", "task_completed",
        "conflict_detected", "reminder_created", "memory_recalled",
    ]
    message: str = ""
    data: dict[str, Any] = {}
    summary: str = ""


class ConfirmationOption(BaseModel):
    id: str
    label: str
    description: str = ""


class LiveContext(BaseModel):
    type: Literal["idle", "task_preview", "conflict", "memory_recalled"] = "idle"
    data: dict[str, Any] = {}


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    events: list[SystemEvent] = []
    live_context: LiveContext | None = None
    requires_confirmation: bool = False
    confirmation_options: list[ConfirmationOption] = []


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str | None = None
    events: list[SystemEvent] = []
