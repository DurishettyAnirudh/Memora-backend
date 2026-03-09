"""Memory schemas."""

from pydantic import BaseModel


class MemoryFact(BaseModel):
    id: int
    fact_type: str
    content: str
    confidence: float | None = None


class MemoryGroup(BaseModel):
    group_name: str
    facts: list[MemoryFact] = []


class MemoryUpdate(BaseModel):
    content: str


class WipeConfirmation(BaseModel):
    confirm: str  # Must be "DELETE_ALL"
