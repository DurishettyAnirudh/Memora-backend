"""Project schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.task import TaskResponse


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    deadline: datetime | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    status: str | None = None


class MilestoneCreate(BaseModel):
    name: str
    target_date: datetime | None = None
    sort_order: int = 0


class MilestoneResponse(BaseModel):
    id: int
    project_id: int
    name: str
    target_date: datetime | None = None
    sort_order: int
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    deadline: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    milestones: list[MilestoneResponse] = []
    tasks: list[TaskResponse] = []
    progress_percent: float = 0.0
