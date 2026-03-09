"""Nudge engine — proactive intelligence for schedule insights."""

from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.project import Project
from app.utils.datetime_helpers import start_of_day, end_of_day, start_of_week, end_of_week


@dataclass
class Nudge:
    nudge_type: str
    title: str
    message: str
    priority: str  # high, medium, low
    data: dict | None = None


class NudgeEngine:
    """Generates proactive insights. Runs on schedule or on-demand."""

    def __init__(self, db: Session):
        self.db = db

    def evaluate_nudges(self) -> list[Nudge]:
        """Run all nudge evaluators and return applicable nudges."""
        nudges = []

        evaluators = [
            self._check_overloaded_days,
            self._check_empty_days,
            self._check_completion_streak,
            self._check_approaching_deadlines,
            self._check_work_life_balance,
            self._check_stale_inbox,
        ]

        for evaluator in evaluators:
            nudge = evaluator()
            if nudge:
                nudges.append(nudge)

        return nudges

    def _check_overloaded_days(self) -> Nudge | None:
        """Flag days with 8+ hours of tasks in the next 7 days."""
        today = date.today()

        for i in range(7):
            day = today + timedelta(days=i)
            day_start = start_of_day(day).isoformat()
            day_end = end_of_day(day).isoformat()

            total_minutes = (
                self.db.query(func.sum(Task.duration_minutes))
                .filter(
                    Task.scheduled_start.isnot(None),
                    Task.scheduled_start >= day_start,
                    Task.scheduled_start <= day_end,
                    Task.status.in_(["pending", "in_progress"]),
                )
                .scalar()
                or 0
            )

            if total_minutes >= 480:  # 8 hours
                return Nudge(
                    nudge_type="overloaded_day",
                    title="Heavy day ahead",
                    message=f"{day.strftime('%A')} has {total_minutes // 60}h of tasks scheduled. Consider moving something?",
                    priority="high",
                    data={"date": day.isoformat(), "total_hours": total_minutes / 60},
                )

        return None

    def _check_empty_days(self) -> Nudge | None:
        """Flag completely empty upcoming weekdays."""
        today = date.today()

        for i in range(1, 8):
            day = today + timedelta(days=i)
            if day.weekday() >= 5:  # Skip weekends
                continue

            day_start = start_of_day(day).isoformat()
            day_end = end_of_day(day).isoformat()

            count = (
                self.db.query(func.count(Task.id))
                .filter(
                    Task.scheduled_start.isnot(None),
                    Task.scheduled_start >= day_start,
                    Task.scheduled_start <= day_end,
                    Task.status.in_(["pending", "in_progress"]),
                )
                .scalar()
                or 0
            )

            if count == 0:
                return Nudge(
                    nudge_type="empty_day",
                    title="Open schedule",
                    message=f"{day.strftime('%A')} is completely free. A good day to tackle inbox items or plan ahead!",
                    priority="low",
                    data={"date": day.isoformat()},
                )

        return None

    def _check_completion_streak(self) -> Nudge | None:
        """Celebrate completion milestones."""
        today = date.today()
        streak = 0

        for i in range(365):
            day = today - timedelta(days=i)
            day_start = start_of_day(day).isoformat()
            day_end = end_of_day(day).isoformat()

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
            else:
                break

        milestones = [3, 7, 14, 21, 30, 60, 90, 100]
        if streak in milestones:
            return Nudge(
                nudge_type="streak",
                title=f"{streak}-day streak!",
                message=f"You've completed tasks {streak} days in a row. Keep it going!",
                priority="low",
                data={"streak": streak},
            )

        return None

    def _check_approaching_deadlines(self) -> Nudge | None:
        """Warn about project deadlines within 3 days."""
        cutoff = (date.today() + timedelta(days=3)).isoformat()
        today_str = date.today().isoformat()

        project = (
            self.db.query(Project)
            .filter(
                Project.status == "active",
                Project.deadline.isnot(None),
                Project.deadline <= cutoff,
                Project.deadline >= today_str,
            )
            .order_by(Project.deadline)
            .first()
        )

        if project:
            return Nudge(
                nudge_type="approaching_deadline",
                title="Deadline approaching",
                message=f"'{project.name}' deadline is {project.deadline}. Check your progress!",
                priority="high",
                data={"project_id": project.id, "deadline": project.deadline},
            )

        return None

    def _check_work_life_balance(self) -> Nudge | None:
        """Alert if work domain exceeds 60% of weekly time."""
        today = date.today()
        ws = start_of_week(today).isoformat()
        we = end_of_week(today).isoformat()

        # Total scheduled minutes this week
        total = (
            self.db.query(func.sum(Task.duration_minutes))
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
                Task.status != "cancelled",
            )
            .scalar()
            or 0
        )

        if total == 0:
            return None

        # Work domain minutes (domain_id=1 assumed as Work)
        from app.models.domain import Domain

        work_domain = (
            self.db.query(Domain).filter(Domain.name == "Work").first()
        )
        if not work_domain:
            return None

        work_minutes = (
            self.db.query(func.sum(Task.duration_minutes))
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
                Task.domain_id == work_domain.id,
                Task.status != "cancelled",
            )
            .scalar()
            or 0
        )

        work_pct = work_minutes / total * 100
        if work_pct > 60:
            return Nudge(
                nudge_type="work_life_balance",
                title="Balance check",
                message=f"Work tasks are {work_pct:.0f}% of your week. Consider scheduling some personal or health time.",
                priority="medium",
                data={"work_percentage": round(work_pct)},
            )

        return None

    def _check_stale_inbox(self) -> Nudge | None:
        """Nudge if inbox has 3+ items older than 2 days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        stale_count = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.is_flexible == True,  # noqa: E712
                Task.status == "pending",
                Task.created_at <= cutoff,
            )
            .scalar()
            or 0
        )

        if stale_count >= 3:
            return Nudge(
                nudge_type="stale_inbox",
                title="Inbox needs attention",
                message=f"You have {stale_count} unscheduled tasks sitting for 2+ days. Want to schedule them?",
                priority="medium",
                data={"stale_count": stale_count},
            )

        return None
