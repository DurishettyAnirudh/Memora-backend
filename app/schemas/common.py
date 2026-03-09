"""Common schemas shared across the application."""

from datetime import datetime

from pydantic import BaseModel


class PaginationParams(BaseModel):
    limit: int = 50
    offset: int = 0


class ErrorResponse(BaseModel):
    detail: str


class SuccessResponse(BaseModel):
    message: str


class SearchResult(BaseModel):
    id: int
    title: str
    description: str | None = None
    snippet: str | None = None
    rank: float = 0.0


class ImportResult(BaseModel):
    tasks_imported: int = 0
    projects_imported: int = 0
    domains_imported: int = 0
    errors: list[str] = []


class BackupRecord(BaseModel):
    id: int
    backup_path: str
    size_bytes: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
