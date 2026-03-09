"""Reminder service — CRUD + scheduling integration."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.reminder import Reminder
from app.models.task import Task
from app.schemas.reminder import ReminderCreate


class ReminderService:
    def __init__(self, db: Session):
        self.db = db

    def list_reminders(
        self,
        task_id: int | None = None,
        is_fired: bool | None = None,
    ) -> list[Reminder]:
        query = self.db.query(Reminder)
        if task_id is not None:
            query = query.filter(Reminder.task_id == task_id)
        if is_fired is not None:
            query = query.filter(Reminder.is_fired == is_fired)
        return query.order_by(Reminder.trigger_at).all()

    def create_reminder(self, data: ReminderCreate) -> Reminder:
        reminder = Reminder(
            task_id=data.task_id,
            reminder_type=data.reminder_type,
            trigger_at=data.trigger_at,
            is_recurring=data.is_recurring or False,
            recurrence_rule=data.recurrence_rule,
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def create_default_reminder(
        self, task: Task, lead_minutes: int = 15
    ) -> Reminder | None:
        """Create a reminder using the user's default lead time."""
        if not task.scheduled_start:
            return None

        if isinstance(task.scheduled_start, str):
            start_dt = datetime.fromisoformat(task.scheduled_start)
        else:
            start_dt = task.scheduled_start
        trigger_at = start_dt - timedelta(minutes=lead_minutes)

        reminder = Reminder(
            task_id=task.id,
            reminder_type="lead_time",
            trigger_at=trigger_at,
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def snooze_reminder(self, reminder_id: int, duration: str) -> Reminder | None:
        """Reschedule trigger. Duration: '5m', '15m', '1h'."""
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return None

        duration_map = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
        }

        delta = duration_map.get(duration, timedelta(minutes=15))
        new_trigger = datetime.now(timezone.utc) + delta

        reminder.snoozed_until = new_trigger
        reminder.is_fired = False
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def dismiss_reminder(self, reminder_id: int) -> bool:
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return False

        reminder.is_dismissed = True
        self.db.commit()
        return True

    def fire_reminder(self, reminder_id: int) -> Reminder | None:
        """Mark as fired. Called by scheduler when trigger time arrives."""
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return None

        reminder.is_fired = True
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_due_reminders(self) -> list[Reminder]:
        """Get unfired, undismissed reminders whose trigger time has passed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return (
            self.db.query(Reminder)
            .filter(
                Reminder.is_fired == False,  # noqa: E712
                Reminder.is_dismissed == False,  # noqa: E712
                Reminder.trigger_at <= now,
            )
            .order_by(Reminder.trigger_at)
            .all()
        )

    def get_snoozed_due(self) -> list[Reminder]:
        """Get snoozed reminders whose snooze time has elapsed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return (
            self.db.query(Reminder)
            .filter(
                Reminder.is_fired == False,  # noqa: E712
                Reminder.is_dismissed == False,  # noqa: E712
                Reminder.snoozed_until.isnot(None),
                Reminder.snoozed_until <= now,
            )
            .order_by(Reminder.snoozed_until)
            .all()
        )
