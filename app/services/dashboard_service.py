"""Dashboard service — today briefing and life metrics aggregation."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.project import Project
from app.services.calendar_service import CalendarService
from app.utils.datetime_helpers import (
    now_utc,
    start_of_day,
    end_of_day,
    start_of_week,
    end_of_week,
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.calendar_service = CalendarService(db)

    def get_today_briefing(self) -> dict:
        """Returns today's tasks, completion count, upcoming, inbox, week load, ring %."""
        today = date.today()
        today_start = start_of_day(today).strftime("%Y-%m-%d %H:%M:%S")
        today_end = end_of_day(today).strftime("%Y-%m-%d %H:%M:%S")

        # Today's scheduled tasks
        todays_tasks = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= today_start,
                Task.scheduled_start <= today_end,
                Task.status != "cancelled",
            )
            .order_by(Task.scheduled_start)
            .all()
        )

        # Completion stats for today
        total_today = len(todays_tasks)
        completed_today = sum(1 for t in todays_tasks if t.status == "completed")
        completion_pct = (
            round(completed_today / total_today * 100) if total_today > 0 else 0
        )

        # Next 3 upcoming tasks (not yet completed, with a time)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        upcoming = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= now,
                Task.status.in_(["pending", "in_progress"]),
            )
            .order_by(Task.scheduled_start)
            .limit(3)
            .all()
        )

        # Inbox count (truly unscheduled — no start time)
        inbox_count = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.scheduled_start.is_(None),
                Task.status == "pending",
            )
            .scalar()
            or 0
        )

        # Week load bars
        week_start = start_of_week(today)
        week_load = self.calendar_service.get_week_load(week_start)

        return {
            "date": today.isoformat(),
            "tasks": [_task_summary(t) for t in todays_tasks],
            "total_tasks": total_today,
            "completed_tasks": completed_today,
            "completion_percentage": completion_pct,
            "upcoming": [_task_summary(t) for t in upcoming],
            "inbox_count": inbox_count,
            "week_load": week_load,
        }

    def get_life_metrics(self, period: str = "week") -> dict:
        """Tasks completed, on-time rate, domain allocation, streak, deadlines."""
        today = date.today()

        if period == "week":
            period_start = start_of_week(today)
            period_end = end_of_week(today)
            prev_start = period_start - timedelta(days=7)
            prev_end = period_start - timedelta(seconds=1)
        else:  # month
            period_start = today.replace(day=1)
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_month - timedelta(days=1)
            prev_start = (period_start - timedelta(days=1)).replace(day=1)
            prev_end = period_start - timedelta(days=1)

        ps = start_of_day(period_start).strftime("%Y-%m-%d %H:%M:%S")
        pe = end_of_day(period_end).strftime("%Y-%m-%d %H:%M:%S")

        # Completed this period
        completed = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= ps,
                Task.completed_at <= pe,
            )
            .scalar()
            or 0
        )

        # Completed previous period
        pps = start_of_day(prev_start).strftime("%Y-%m-%d %H:%M:%S")
        ppe = end_of_day(prev_end).strftime("%Y-%m-%d %H:%M:%S")
        prev_completed = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= pps,
                Task.completed_at <= ppe,
            )
            .scalar()
            or 0
        )

        # On-time rate: tasks completed before or on their scheduled_end
        on_time = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= ps,
                Task.completed_at <= pe,
                Task.scheduled_end.isnot(None),
                Task.completed_at <= Task.scheduled_end,
            )
            .scalar()
            or 0
        )
        on_time_rate = round(on_time / completed * 100) if completed > 0 else 100

        # Domain time allocation
        domain_stats = (
            self.db.query(
                Task.domain_id,
                func.sum(Task.duration_minutes),
                func.count(Task.id),
            )
            .filter(
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= ps,
                Task.completed_at <= pe,
            )
            .group_by(Task.domain_id)
            .all()
        )

        domain_allocation = [
            {
                "domain_id": d_id,
                "total_minutes": total or 0,
                "task_count": count,
            }
            for d_id, total, count in domain_stats
        ]

        # Completion streak (consecutive days with ≥1 completed task)
        streak = self._calculate_streak(today)

        # Upcoming deadlines (projects with deadlines in next 7 days)
        deadline_cutoff = (today + timedelta(days=7)).isoformat()
        upcoming_deadlines = (
            self.db.query(Project)
            .filter(
                Project.status == "active",
                Project.deadline.isnot(None),
                Project.deadline <= deadline_cutoff,
            )
            .order_by(Project.deadline)
            .all()
        )

        return {
            "period": period,
            "tasks_completed": completed,
            "prev_period_completed": prev_completed,
            "change_pct": (
                round((completed - prev_completed) / max(prev_completed, 1) * 100)
            ),
            "on_time_rate": on_time_rate,
            "domain_allocation": domain_allocation,
            "streak_days": streak,
            "upcoming_deadlines": [
                {
                    "id": p.id,
                    "name": p.name,
                    "deadline": p.deadline,
                }
                for p in upcoming_deadlines
            ],
        }

    def _calculate_streak(self, today: date) -> int:
        """Count consecutive days going backwards that have ≥1 completed task."""
        streak = 0
        current = today

        for _ in range(365):  # max lookback
            day_start = start_of_day(current).strftime("%Y-%m-%d %H:%M:%S")
            day_end = end_of_day(current).strftime("%Y-%m-%d %H:%M:%S")

            count = (
                self.db.query(func.count(Task.id))
                .filter(
                    Task.status == "completed",
                    Task.completed_at.isnot(None),
                    Task.completed_at >= day_start,
                    Task.completed_at <= day_end,
                )
                .scalar()
                or 0
            )

            if count > 0:
                streak += 1
                current -= timedelta(days=1)
            else:
                break

        return streak


def _task_summary(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "scheduled_start": task.scheduled_start,
        "scheduled_end": task.scheduled_end,
        "duration_minutes": task.duration_minutes,
        "domain_id": task.domain_id,
        "priority": task.priority,
        "status": task.status,
    }
