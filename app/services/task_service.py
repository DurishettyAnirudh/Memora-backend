"""Task service — CRUD and business logic for tasks."""

from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, BulkOperation, BulkResult


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def list_tasks(
        self,
        domain_id: int | None = None,
        status: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        project_id: int | None = None,
        is_flexible: bool | None = None,
        sort: str = "scheduled_start",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        query = self.db.query(Task)

        if domain_id is not None:
            query = query.filter(Task.domain_id == domain_id)
        if status is not None:
            query = query.filter(Task.status == status)
        if start is not None:
            query = query.filter(Task.scheduled_start >= start)
        if end is not None:
            query = query.filter(Task.scheduled_start <= end)
        if project_id is not None:
            query = query.filter(Task.project_id == project_id)
        if is_flexible is not None:
            query = query.filter(Task.is_flexible == is_flexible)

        # Sort
        if sort == "scheduled_start":
            query = query.order_by(Task.scheduled_start.asc().nullslast())
        elif sort == "priority":
            # high > medium > low
            query = query.order_by(Task.priority.asc())
        elif sort == "created_at":
            query = query.order_by(Task.created_at.desc())
        else:
            query = query.order_by(Task.scheduled_start.asc().nullslast())

        return query.offset(offset).limit(limit).all()

    def get_task(self, task_id: int) -> Task | None:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def create_task(self, data: TaskCreate) -> Task:
        task_data = data.model_dump()
        # Auto-compute scheduled_end if start and duration given
        if task_data.get("scheduled_start") and task_data.get("duration_minutes"):
            if not task_data.get("scheduled_end"):
                task_data["scheduled_end"] = task_data["scheduled_start"] + timedelta(
                    minutes=task_data["duration_minutes"]
                )
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task(self, task_id: int, data: TaskUpdate) -> Task | None:
        task = self.get_task(task_id)
        if not task:
            return None
        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(task, key, value)

        # Recompute end if start or duration changed
        if ("scheduled_start" in update_data or "duration_minutes" in update_data):
            if task.scheduled_start and task.duration_minutes:
                task.scheduled_end = task.scheduled_start + timedelta(
                    minutes=task.duration_minutes
                )

        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        self.db.delete(task)
        self.db.commit()
        return True

    def complete_task(self, task_id: int) -> Task | None:
        task = self.get_task(task_id)
        if not task:
            return None
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_inbox(self, limit: int = 50, offset: int = 0) -> list[Task]:
        """Get flexible/unscheduled tasks that are still pending."""
        return (
            self.db.query(Task)
            .filter(Task.is_flexible == True, Task.status == "pending")  # noqa: E712
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_inbox_count(self) -> int:
        return (
            self.db.query(Task)
            .filter(Task.is_flexible == True, Task.status == "pending")  # noqa: E712
            .count()
        )

    def bulk_operation(self, data: BulkOperation) -> BulkResult:
        tasks = self.db.query(Task).filter(Task.id.in_(data.task_ids)).all()
        affected_ids = []
        errors = []

        for task in tasks:
            try:
                if data.operation == "complete_all":
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)
                elif data.operation == "delete":
                    self.db.delete(task)
                elif data.operation == "reschedule":
                    if data.reschedule_to:
                        delta = data.reschedule_to - (task.scheduled_start or data.reschedule_to)
                        task.scheduled_start = data.reschedule_to
                        if task.scheduled_end:
                            task.scheduled_end = task.scheduled_end + delta
                    elif data.reschedule_delta_days:
                        delta = timedelta(days=data.reschedule_delta_days)
                        if task.scheduled_start:
                            task.scheduled_start = task.scheduled_start + delta
                        if task.scheduled_end:
                            task.scheduled_end = task.scheduled_end + delta
                affected_ids.append(task.id)
            except Exception as e:
                errors.append(f"Task {task.id}: {str(e)}")

        self.db.commit()
        return BulkResult(
            affected_count=len(affected_ids),
            task_ids=affected_ids,
            errors=errors,
        )

    def get_tasks_in_range(self, start: datetime, end: datetime) -> list[Task]:
        """Get all non-flexible, scheduled tasks in a time range."""
        return (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start < end,
                Task.scheduled_end > start,
                Task.status.in_(["pending", "in_progress"]),
            )
            .order_by(Task.scheduled_start)
            .all()
        )

    def get_tasks_for_date(self, target_date: datetime) -> list[Task]:
        """Get all tasks scheduled for a specific date."""
        from app.utils.datetime_helpers import start_of_day, end_of_day
        day_start = start_of_day(target_date.date() if isinstance(target_date, datetime) else target_date)
        day_end = end_of_day(target_date.date() if isinstance(target_date, datetime) else target_date)
        return self.get_tasks_in_range(day_start, day_end)
