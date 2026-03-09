"""Calendar service — filtered views, availability, week load."""

from datetime import date, datetime, timedelta, time, timezone

from sqlalchemy.orm import Session

from app.models.task import Task
from app.services.recurrence_service import RecurrenceService
from app.utils.datetime_helpers import start_of_day, end_of_day, start_of_week, end_of_week


class CalendarService:
    def __init__(self, db: Session):
        self.db = db
        self.recurrence_service = RecurrenceService(db)

    def get_events(
        self,
        start: date,
        end: date,
        domains: list[int] | None = None,
        view: str = "week",
    ) -> list[dict]:
        """Fetch tasks in range, expand recurrences, merge, sort."""
        range_start = datetime.combine(start, time.min)
        range_end = datetime.combine(end, time.max)

        query = self.db.query(Task).filter(
            Task.status != "cancelled",
        )

        if domains:
            query = query.filter(Task.domain_id.in_(domains))

        # Get non-recurring tasks in range
        non_recurring = query.filter(
            Task.is_recurring == False,  # noqa: E712
            Task.scheduled_start.isnot(None),
            Task.scheduled_start <= range_end.strftime("%Y-%m-%d %H:%M:%S"),
            Task.scheduled_end >= range_start.strftime("%Y-%m-%d %H:%M:%S"),
        ).all()

        events = [self._task_to_event(t) for t in non_recurring]

        # Get recurring tasks and expand
        recurring_tasks = query.filter(Task.is_recurring == True).all()  # noqa: E712
        for task in recurring_tasks:
            instances = self.recurrence_service.expand_recurrence(
                task, range_start, range_end
            )
            events.extend(instances)

        # Also include flexible/unscheduled tasks if view is "agenda"
        if view == "agenda":
            flexible = query.filter(
                Task.is_flexible == True,  # noqa: E712
                Task.status == "pending",
            ).all()
            events.extend([self._task_to_event(t) for t in flexible])

        events.sort(key=lambda e: e.get("scheduled_start") or "9999")
        return events

    def get_day_view(self, target_date: date) -> dict:
        """Hour-by-hour breakdown for timeline rendering."""
        events = self.get_events(target_date, target_date, view="day")

        hours = {}
        for hour in range(0, 24):
            hours[hour] = []

        for event in events:
            start_str = event.get("scheduled_start")
            if not start_str:
                continue
            if isinstance(start_str, datetime):
                start_dt = start_str
            else:
                start_dt = datetime.fromisoformat(str(start_str))
            hours[start_dt.hour].append(event)

        return {
            "date": target_date.isoformat(),
            "hours": hours,
            "total_events": len(events),
            "total_minutes": sum(e.get("duration_minutes", 0) or 0 for e in events),
        }

    def get_availability(
        self, target_date: date, duration_minutes: int
    ) -> list[dict]:
        """Return free time slots of at least `duration_minutes` on a given day."""
        events = self.get_events(target_date, target_date, view="day")

        # Collect occupied intervals
        occupied = []
        for event in events:
            start_str = event.get("scheduled_start")
            end_str = event.get("scheduled_end")
            if start_str and end_str:
                s = start_str if isinstance(start_str, datetime) else datetime.fromisoformat(str(start_str))
                e = end_str if isinstance(end_str, datetime) else datetime.fromisoformat(str(end_str))
                occupied.append((s, e))

        occupied.sort(key=lambda x: x[0])

        # Find gaps on the day (6 AM to 11 PM window)
        day_start = datetime.combine(target_date, time(6, 0), tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, time(23, 0), tzinfo=timezone.utc)

        free_slots = []
        current = day_start

        for occ_start, occ_end in occupied:
            if occ_start > current:
                gap = (occ_start - current).total_seconds() / 60
                if gap >= duration_minutes:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": occ_start.isoformat(),
                        "duration_minutes": int(gap),
                    })
            if occ_end > current:
                current = occ_end

        # Check remaining time after last event
        if current < day_end:
            gap = (day_end - current).total_seconds() / 60
            if gap >= duration_minutes:
                free_slots.append({
                    "start": current.isoformat(),
                    "end": day_end.isoformat(),
                    "duration_minutes": int(gap),
                })

        return free_slots

    def get_week_load(self, week_start: date) -> list[dict]:
        """Task count + total hours per day for 7 days."""
        days = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            events = self.get_events(day, day, view="day")

            total_minutes = sum(e.get("duration_minutes", 0) or 0 for e in events)
            days.append({
                "date": day.isoformat(),
                "task_count": len(events),
                "total_hours": round(total_minutes / 60, 1),
            })

        return days

    def find_best_slot(
        self,
        duration_minutes: int,
        date_range: tuple[date, date],
        preferred_time: str | None = None,
    ) -> list[dict]:
        """Find best available slots within a date range, ranked by preference."""
        suggestions = []
        current = date_range[0]

        while current <= date_range[1] and len(suggestions) < 3:
            slots = self.get_availability(current, duration_minutes)

            for slot in slots:
                slot_start = datetime.fromisoformat(slot["start"])
                hour = slot_start.hour

                # Score by preferred time of day
                score = 50  # base score
                if preferred_time == "morning" and 6 <= hour < 12:
                    score += 30
                elif preferred_time == "afternoon" and 12 <= hour < 17:
                    score += 30
                elif preferred_time == "evening" and 17 <= hour < 23:
                    score += 30
                # Prefer working hours
                if 9 <= hour < 17:
                    score += 10

                suggestions.append({
                    "start": slot["start"],
                    "end_limit": slot["end"],
                    "date": current.isoformat(),
                    "score": score,
                })

            current += timedelta(days=1)

        suggestions.sort(key=lambda s: s["score"], reverse=True)
        return suggestions[:3]

    @staticmethod
    def _task_to_event(task: Task) -> dict:
        return {
            "task_id": task.id,
            "title": task.title,
            "scheduled_start": task.scheduled_start,
            "scheduled_end": task.scheduled_end,
            "duration_minutes": task.duration_minutes,
            "domain_id": task.domain_id,
            "priority": task.priority,
            "status": task.status,
            "is_recurring": task.is_recurring,
            "is_flexible": task.is_flexible,
        }
