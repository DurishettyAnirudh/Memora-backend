"""Conflict detection and resolution engine."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.task import Task
from app.utils.datetime_helpers import time_ranges_overlap, minutes_between


@dataclass
class Conflict:
    type: str  # TIME_OVERLAP, NO_BUFFER, DAILY_OVERLOAD, WEEKLY_OVERLOAD
    task_a_id: int
    task_b_id: int | None
    description: str
    severity: str = "medium"  # high, medium, low


@dataclass
class Resolution:
    id: str
    label: str
    description: str
    action: str  # move_to_next_free, shorten_existing, push_to_tomorrow, swap_order, add_buffer
    new_start: datetime | None = None
    new_end: datetime | None = None


@dataclass
class DailyLoad:
    total_minutes: int
    task_count: int
    is_overloaded: bool


class ConflictEngine:
    """O(n log n) interval overlap detection with configurable buffer."""

    def __init__(self, buffer_minutes: int = 10, daily_limit_hours: float = 8.0):
        self.buffer_minutes = buffer_minutes
        self.daily_limit_minutes = int(daily_limit_hours * 60)

    def check_conflicts(
        self, new_task: Task, existing_tasks: list[Task]
    ) -> list[Conflict]:
        """Returns all conflicts for a new/updated task against existing schedule."""
        conflicts = []

        if not new_task.scheduled_start or not new_task.scheduled_end:
            return conflicts

        new_start = new_task.scheduled_start
        new_end = new_task.scheduled_end

        for existing in existing_tasks:
            if existing.id == new_task.id:
                continue
            if not existing.scheduled_start or not existing.scheduled_end:
                continue

            ex_start = existing.scheduled_start
            ex_end = existing.scheduled_end

            # Check direct time overlap
            if time_ranges_overlap(new_start, new_end, ex_start, ex_end):
                conflicts.append(Conflict(
                    type="TIME_OVERLAP",
                    task_a_id=new_task.id,
                    task_b_id=existing.id,
                    description=(
                        f'"{new_task.title}" overlaps with "{existing.title}"'
                    ),
                    severity="high",
                ))
            # Check buffer (back-to-back)
            elif self.buffer_minutes > 0:
                gap_after = minutes_between(new_end, ex_start)
                gap_before = minutes_between(ex_end, new_start)
                if 0 <= gap_after < self.buffer_minutes or 0 <= gap_before < self.buffer_minutes:
                    conflicts.append(Conflict(
                        type="NO_BUFFER",
                        task_a_id=new_task.id,
                        task_b_id=existing.id,
                        description=(
                            f'"{new_task.title}" is back-to-back with "{existing.title}" '
                            f"(less than {self.buffer_minutes}min buffer)"
                        ),
                        severity="low",
                    ))

        # Check daily overload
        daily_load = self._calculate_daily_load_with_new(
            new_task, existing_tasks, new_start.date()
        )
        if daily_load.is_overloaded:
            conflicts.append(Conflict(
                type="DAILY_OVERLOAD",
                task_a_id=new_task.id,
                task_b_id=None,
                description=(
                    f"Adding this task brings the day to "
                    f"{daily_load.total_minutes / 60:.1f}h "
                    f"(limit: {self.daily_limit_minutes / 60:.1f}h)"
                ),
                severity="medium",
            ))

        return conflicts

    def generate_resolutions(
        self, conflict: Conflict, new_task: Task, existing_tasks: list[Task]
    ) -> list[Resolution]:
        """Generates 2-3 ranked resolution options for a conflict."""
        resolutions = []

        if not new_task.scheduled_start or not new_task.scheduled_end:
            return resolutions

        duration = minutes_between(new_task.scheduled_start, new_task.scheduled_end)
        target_date = new_task.scheduled_start.date()

        # Option A: Find next free slot on same day
        next_slot = self.find_next_free_slot(duration, target_date, existing_tasks)
        if next_slot:
            resolutions.append(Resolution(
                id="move_same_day",
                label="Move to next free slot",
                description=f"Move to {next_slot.strftime('%I:%M %p')}",
                action="move_to_next_free",
                new_start=next_slot,
                new_end=next_slot + timedelta(minutes=duration),
            ))

        # Option B: Push to next day
        next_day = target_date + timedelta(days=1)
        next_day_slot = self.find_next_free_slot(
            duration, next_day, existing_tasks, start_hour=9
        )
        if next_day_slot:
            resolutions.append(Resolution(
                id="push_tomorrow",
                label="Push to tomorrow",
                description=f"Move to {next_day_slot.strftime('%a %I:%M %p')}",
                action="push_to_tomorrow",
                new_start=next_day_slot,
                new_end=next_day_slot + timedelta(minutes=duration),
            ))

        # Option C: Keep anyway (acknowledge conflict)
        resolutions.append(Resolution(
            id="keep_anyway",
            label="Keep as scheduled",
            description="Accept the scheduling conflict",
            action="keep",
            new_start=new_task.scheduled_start,
            new_end=new_task.scheduled_end,
        ))

        return resolutions

    def find_next_free_slot(
        self,
        duration_minutes: int,
        target_date,
        existing_tasks: list[Task],
        start_hour: int = 6,
        end_hour: int = 23,
    ) -> datetime | None:
        """Finds the earliest free slot of given duration on a given day."""
        from datetime import time as _time

        day_start = datetime.combine(target_date, _time(hour=start_hour))
        day_end = datetime.combine(target_date, _time(hour=end_hour))

        # Collect all busy intervals for this day
        busy = []
        for task in existing_tasks:
            if not task.scheduled_start or not task.scheduled_end:
                continue
            if task.scheduled_start.date() == target_date:
                busy.append((task.scheduled_start, task.scheduled_end))

        busy.sort(key=lambda x: x[0])

        # Find gaps
        current = day_start
        for b_start, b_end in busy:
            if current + timedelta(minutes=duration_minutes) <= b_start:
                return current
            if b_end > current:
                current = b_end + timedelta(minutes=self.buffer_minutes)

        # Check after last busy slot
        if current + timedelta(minutes=duration_minutes) <= day_end:
            return current

        return None

    def calculate_daily_load(
        self, target_date, tasks: list[Task]
    ) -> DailyLoad:
        """Returns total scheduled hours for a day."""
        total = 0
        count = 0
        for task in tasks:
            if not task.scheduled_start or not task.scheduled_end:
                continue
            if task.scheduled_start.date() == target_date:
                total += minutes_between(task.scheduled_start, task.scheduled_end)
                count += 1

        return DailyLoad(
            total_minutes=total,
            task_count=count,
            is_overloaded=total > self.daily_limit_minutes,
        )

    def _calculate_daily_load_with_new(
        self, new_task: Task, existing_tasks: list[Task], target_date
    ) -> DailyLoad:
        """Calculate daily load including a new task."""
        all_tasks = list(existing_tasks) + [new_task]
        return self.calculate_daily_load(target_date, all_tasks)
