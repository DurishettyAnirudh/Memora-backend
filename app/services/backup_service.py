"""Backup service — export, import, backup, wipe."""

import csv
import io
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.backup import BackupLog
from app.models.domain import Domain
from app.models.project import Project, Milestone
from app.models.reminder import Reminder
from app.models.settings import UserSettings
from app.models.task import Task, TaskRecurrenceException


class BackupService:
    def __init__(self, db: Session):
        self.db = db

    def export_json(self) -> dict:
        """Export all app data as JSON."""
        domains = self.db.query(Domain).all()
        tasks = self.db.query(Task).all()
        projects = self.db.query(Project).all()
        milestones = self.db.query(Milestone).all()
        reminders = self.db.query(Reminder).all()
        exceptions = self.db.query(TaskRecurrenceException).all()
        user_settings = self.db.query(UserSettings).first()

        return {
            "version": "2.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "domains": [_model_to_dict(d) for d in domains],
            "tasks": [_model_to_dict(t) for t in tasks],
            "projects": [_model_to_dict(p) for p in projects],
            "milestones": [_model_to_dict(m) for m in milestones],
            "reminders": [_model_to_dict(r) for r in reminders],
            "task_recurrence_exceptions": [_model_to_dict(e) for e in exceptions],
            "settings": _model_to_dict(user_settings) if user_settings else None,
        }

    def export_csv(self) -> str:
        """Export tasks as CSV string."""
        tasks = self.db.query(Task).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        columns = [
            "id", "title", "description", "domain_id", "priority", "status",
            "scheduled_start", "scheduled_end", "duration_minutes",
            "is_flexible", "is_recurring", "project_id", "completed_at",
            "created_at", "updated_at",
        ]
        writer.writerow(columns)

        for task in tasks:
            writer.writerow([getattr(task, col, None) for col in columns])

        return output.getvalue()

    def import_json(self, data: dict) -> dict:
        """Import from JSON backup. Transactional."""
        version = data.get("version", "1.0")
        imported = {"domains": 0, "tasks": 0, "projects": 0, "milestones": 0, "reminders": 0}

        try:
            # Import domains
            for item in data.get("domains", []):
                domain = Domain(
                    name=item["name"],
                    color=item.get("color", "#C0C0C0"),
                    sort_order=item.get("sort_order", 0),
                    is_archived=item.get("is_archived", False),
                )
                self.db.add(domain)
                imported["domains"] += 1

            self.db.flush()

            # Import projects
            for item in data.get("projects", []):
                project = Project(
                    name=item["name"],
                    description=item.get("description"),
                    deadline=item.get("deadline"),
                    status=item.get("status", "active"),
                )
                self.db.add(project)
                imported["projects"] += 1

            self.db.flush()

            # Import tasks
            for item in data.get("tasks", []):
                task = Task(
                    title=item["title"],
                    description=item.get("description"),
                    domain_id=item.get("domain_id"),
                    priority=item.get("priority", "medium"),
                    status=item.get("status", "pending"),
                    scheduled_start=item.get("scheduled_start"),
                    scheduled_end=item.get("scheduled_end"),
                    duration_minutes=item.get("duration_minutes"),
                    is_flexible=item.get("is_flexible", False),
                    is_recurring=item.get("is_recurring", False),
                    recurrence_rule=item.get("recurrence_rule"),
                    project_id=item.get("project_id"),
                )
                self.db.add(task)
                imported["tasks"] += 1

            self.db.flush()

            # Import reminders
            for item in data.get("reminders", []):
                reminder = Reminder(
                    task_id=item["task_id"],
                    reminder_type=item.get("reminder_type", "point"),
                    trigger_at=item["trigger_at"],
                    is_recurring=item.get("is_recurring", False),
                    recurrence_rule=item.get("recurrence_rule"),
                )
                self.db.add(reminder)
                imported["reminders"] += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "success": True,
            "version": version,
            "imported": imported,
        }

    def create_backup(self, backup_dir: str | None = None) -> dict:
        """Copy memora.db to backup directory with timestamp."""
        db_path = Path(settings.DB_PATH)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        if backup_dir:
            target_dir = Path(backup_dir)
        else:
            target_dir = db_path.parent / "backups"

        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"memora_backup_{timestamp}.db"
        backup_path = target_dir / backup_name

        shutil.copy2(str(db_path), str(backup_path))

        size_bytes = backup_path.stat().st_size

        # Log the backup
        log = BackupLog(
            backup_path=str(backup_path),
            size_bytes=size_bytes,
        )
        self.db.add(log)
        self.db.commit()

        return {
            "backup_path": str(backup_path),
            "size_bytes": size_bytes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def wipe_all_data(self, confirmation: str) -> bool:
        """Delete all rows from all app tables. Requires explicit confirmation."""
        if confirmation != "WIPE_ALL_DATA":
            return False

        try:
            self.db.query(TaskRecurrenceException).delete()
            self.db.query(Reminder).delete()
            self.db.query(Task).delete()
            self.db.query(Milestone).delete()
            self.db.query(Project).delete()
            self.db.query(Domain).delete()
            self.db.query(BackupLog).delete()
            self.db.query(UserSettings).delete()
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise


def _model_to_dict(obj) -> dict:
    """Convert SQLAlchemy model instance to dict."""
    if obj is None:
        return {}
    return {
        c.name: getattr(obj, c.name)
        for c in obj.__table__.columns
    }
