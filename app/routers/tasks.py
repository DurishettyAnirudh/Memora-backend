"""Task routes — CRUD, inbox, bulk operations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, BulkOperation, BulkResult
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    domain_id: int | None = None,
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
    project_id: int | None = None,
    is_flexible: bool | None = None,
    sort: str = "scheduled_start",
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    return service.list_tasks(
        domain_id=domain_id,
        status=status,
        start=start,
        end=end,
        project_id=project_id,
        is_flexible=is_flexible,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/inbox", response_model=list[TaskResponse])
def get_inbox(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    return service.get_inbox(limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.create_task(data)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.update_task(task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    service = TaskService(db)
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.complete_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/bulk", response_model=BulkResult)
def bulk_operation(data: BulkOperation, db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.bulk_operation(data)
