"""Domain schemas."""

from datetime import datetime

from pydantic import BaseModel


class DomainCreate(BaseModel):
    name: str
    color: str
    sort_order: int = 0


class DomainUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    sort_order: int | None = None
    is_archived: bool | None = None


class DomainResponse(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
