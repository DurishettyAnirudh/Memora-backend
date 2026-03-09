"""Project routes — CRUD + progress tracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    MilestoneCreate,
    MilestoneResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(status: str | None = None, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.list_projects(status=status)


@router.get("/{project_id}")
def get_project_detail(project_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    detail = service.get_project_detail(project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Project not found")
    return detail


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.create_project(data)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)
):
    service = ProjectService(db)
    project = service.update_project(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    if not service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/progress")
def get_progress(project_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    if not service.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return service.get_progress(project_id)


@router.get("/{project_id}/risk")
def get_risk(project_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    if not service.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return service.is_at_risk(project_id)


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
def create_milestone(
    project_id: int, data: MilestoneCreate, db: Session = Depends(get_db)
):
    service = ProjectService(db)
    milestone = service.create_milestone(project_id, data)
    if not milestone:
        raise HTTPException(status_code=404, detail="Project not found")
    return milestone


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
def complete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    milestone = service.complete_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone
