"""Project service — CRUD + progress tracking."""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.project import Project, Milestone
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate, MilestoneCreate


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def list_projects(self, status: str | None = None) -> list[Project]:
        query = self.db.query(Project)
        if status:
            query = query.filter(Project.status == status)
        return query.order_by(Project.created_at.desc()).all()

    def get_project(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name,
            description=data.description,
            deadline=data.deadline,
            status="active",
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update_project(self, project_id: int, data: ProjectUpdate) -> Project | None:
        project = self.get_project(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        project.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: int) -> bool:
        project = self.get_project(project_id)
        if not project:
            return False

        self.db.delete(project)
        self.db.commit()
        return True

    def get_progress(self, project_id: int) -> dict:
        """Calculate project completion % from task statuses."""
        total = (
            self.db.query(func.count(Task.id))
            .filter(Task.project_id == project_id, Task.status != "cancelled")
            .scalar()
            or 0
        )
        completed = (
            self.db.query(func.count(Task.id))
            .filter(Task.project_id == project_id, Task.status == "completed")
            .scalar()
            or 0
        )

        return {
            "project_id": project_id,
            "total_tasks": total,
            "completed_tasks": completed,
            "percentage": round(completed / total * 100) if total > 0 else 0,
        }

    def is_at_risk(self, project_id: int) -> dict:
        """Check if project is behind schedule relative to deadline."""
        project = self.get_project(project_id)
        if not project or not project.deadline:
            return {"at_risk": False, "reason": None}

        progress = self.get_progress(project_id)
        deadline = datetime.fromisoformat(project.deadline)
        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(project.created_at)

        total_duration = (deadline - created).total_seconds()
        elapsed = (now - created).total_seconds()

        if total_duration <= 0:
            return {"at_risk": True, "reason": "deadline_passed"}

        time_pct = min(100, round(elapsed / total_duration * 100))

        # At risk if time elapsed % is significantly ahead of completion %
        at_risk = time_pct > progress["percentage"] + 20

        return {
            "at_risk": at_risk,
            "reason": "behind_schedule" if at_risk else None,
            "time_elapsed_pct": time_pct,
            "completion_pct": progress["percentage"],
        }

    # --- Milestone operations ---

    def create_milestone(
        self, project_id: int, data: MilestoneCreate
    ) -> Milestone | None:
        project = self.get_project(project_id)
        if not project:
            return None

        # Get next sort_order
        max_order = (
            self.db.query(func.max(Milestone.sort_order))
            .filter(Milestone.project_id == project_id)
            .scalar()
            or 0
        )

        milestone = Milestone(
            project_id=project_id,
            name=data.name,
            target_date=data.target_date,
            sort_order=max_order + 1,
        )
        self.db.add(milestone)
        self.db.commit()
        self.db.refresh(milestone)
        return milestone

    def complete_milestone(self, milestone_id: int) -> Milestone | None:
        milestone = (
            self.db.query(Milestone).filter(Milestone.id == milestone_id).first()
        )
        if not milestone:
            return None

        milestone.is_completed = True
        self.db.commit()
        self.db.refresh(milestone)
        return milestone

    def get_project_detail(self, project_id: int) -> dict | None:
        """Full project detail with tasks grouped by status, milestones, progress."""
        project = self.get_project(project_id)
        if not project:
            return None

        tasks = (
            self.db.query(Task)
            .filter(Task.project_id == project_id)
            .order_by(Task.created_at)
            .all()
        )

        milestones = (
            self.db.query(Milestone)
            .filter(Milestone.project_id == project_id)
            .order_by(Milestone.sort_order)
            .all()
        )

        progress = self.get_progress(project_id)
        risk = self.is_at_risk(project_id)

        # Group tasks by status
        grouped_tasks = {}
        for task in tasks:
            status = task.status
            if status not in grouped_tasks:
                grouped_tasks[status] = []
            grouped_tasks[status].append(task)

        return {
            "project": project,
            "tasks_by_status": grouped_tasks,
            "milestones": milestones,
            "progress": progress,
            "risk": risk,
        }
