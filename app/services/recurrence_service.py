"""Recurrence service — expand and manage recurring tasks."""

from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrulestr

from sqlalchemy.orm import Session

from app.models.task import Task, TaskRecurrenceException


class RecurrenceService:
    def __init__(self, db: Session):
        self.db = db

    def expand_recurrence(
        self, task: Task, range_start: datetime, range_end: datetime
    ) -> list[dict]:
        """Generate virtual task instances from a recurring task within a date range."""
        if not task.is_recurring or not task.recurrence_rule:
            return []

        try:
            rule = rrulestr(task.recurrence_rule, dtstart=task.scheduled_start)
        except (ValueError, TypeError):
            return []

        # Get exceptions for this task
        exceptions = (
            self.db.query(TaskRecurrenceException)
            .filter(TaskRecurrenceException.task_id == task.id)
            .all()
        )
        exception_dates = {ex.original_date for ex in exceptions if ex.is_deleted}
        exception_overrides = {
            ex.original_date: ex for ex in exceptions if not ex.is_deleted
        }

        instances = []
        duration = timedelta(minutes=task.duration_minutes or 60)

        for dt in rule.between(range_start, range_end, inc=True):
            date_key = dt.strftime("%Y-%m-%d")

            # Skip deleted occurrences
            if date_key in exception_dates:
                continue

            # Check for overrides
            override = exception_overrides.get(date_key)
            if override:
                instance_start = (
                    datetime.fromisoformat(override.new_start)
                    if override.new_start
                    else dt
                )
                instance_end = (
                    datetime.fromisoformat(override.new_end)
                    if override.new_end
                    else instance_start + duration
                )
                title = override.new_title or task.title
            else:
                instance_start = dt
                instance_end = dt + duration
                title = task.title

            instances.append({
                "task_id": task.id,
                "title": title,
                "scheduled_start": instance_start,
                "scheduled_end": instance_end,
                "domain_id": task.domain_id,
                "priority": task.priority,
                "status": task.status,
                "is_recurring": True,
                "original_date": date_key,
            })

        return instances

    def edit_occurrence(
        self, task: Task, original_date: str, scope: str, **kwargs
    ) -> Task | TaskRecurrenceException:
        """
        Edit a recurring task occurrence.
        scope: 'this_only' | 'this_and_future' | 'all'
        """
        if scope == "this_only":
            exception = TaskRecurrenceException(
                task_id=task.id,
                original_date=original_date,
                new_start=kwargs.get("new_start"),
                new_end=kwargs.get("new_end"),
                new_title=kwargs.get("new_title"),
                is_deleted=kwargs.get("is_deleted", False),
            )
            self.db.add(exception)
            self.db.commit()
            self.db.refresh(exception)
            return exception

        elif scope == "this_and_future":
            # End the current recurrence before this date
            # and create a new task with the updated rule starting from this date
            original_dt = datetime.fromisoformat(original_date)

            # Modify the UNTIL of the existing rule
            if "UNTIL=" not in (task.recurrence_rule or ""):
                until_str = (original_dt - timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
                task.recurrence_rule = f"{task.recurrence_rule};UNTIL={until_str}"
            self.db.commit()

            # Return the modified original task
            return task

        elif scope == "all":
            # Update the task itself
            for key, value in kwargs.items():
                if hasattr(task, key) and value is not None:
                    setattr(task, key, value)
            self.db.commit()
            self.db.refresh(task)
            return task

        return task

    def delete_occurrence(self, task: Task, original_date: str) -> TaskRecurrenceException:
        """Delete a single occurrence of a recurring task."""
        return self.edit_occurrence(task, original_date, "this_only", is_deleted=True)
