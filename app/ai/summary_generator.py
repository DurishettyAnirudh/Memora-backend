"""Summary generator — daily, weekly, project summaries."""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.client import chat_completion
from app.ai.prompts.summary_generator import (
    DAILY_SUMMARY_PROMPT,
    WEEKLY_SUMMARY_PROMPT,
    PROJECT_STATUS_PROMPT,
)
from app.models.task import Task
from app.models.project import Project
from app.utils.datetime_helpers import start_of_day, end_of_day, start_of_week, end_of_week


class SummaryGenerator:
    """Generates natural language summaries and reflections."""

    def __init__(self, db: Session):
        self.db = db

    def daily_summary(self, target_date: date | None = None) -> str:
        """Generate an end-of-day summary."""
        d = target_date or date.today()
        ds = start_of_day(d).isoformat()
        de = end_of_day(d).isoformat()

        tasks = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ds,
                Task.scheduled_start <= de,
            )
            .all()
        )

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")

        schedule = "\n".join(
            f"- {'✓' if t.status == 'completed' else '○'} {t.title} ({t.scheduled_start})"
            for t in tasks
        ) or "No tasks today."

        # Domain breakdown
        by_domain: dict[int | None, int] = {}
        for t in tasks:
            by_domain[t.domain_id] = by_domain.get(t.domain_id, 0) + 1
        domain_text = ", ".join(f"domain {k}: {v}" for k, v in by_domain.items())

        prompt = DAILY_SUMMARY_PROMPT.format(
            schedule=schedule,
            completed_count=completed,
            total_count=total,
            domain_breakdown=domain_text or "N/A",
        )

        try:
            return chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.5,
                max_tokens=4096,
            )
        except Exception:
            return f"Today: {completed}/{total} tasks completed."

    def weekly_summary(self, week_start: date | None = None) -> str:
        """Generate a weekly summary."""
        ws_date = week_start or start_of_week(date.today())
        we_date = ws_date + timedelta(days=6)
        ws = start_of_day(ws_date).isoformat()
        we = end_of_day(we_date).isoformat()

        completed = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= ws,
                Task.completed_at <= we,
            )
            .scalar()
            or 0
        )

        total = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
            )
            .scalar()
            or 0
        )

        on_time_rate = 100
        if completed > 0:
            on_time = (
                self.db.query(func.count(Task.id))
                .filter(
                    Task.status == "completed",
                    Task.completed_at.isnot(None),
                    Task.completed_at >= ws,
                    Task.completed_at <= we,
                    Task.scheduled_end.isnot(None),
                    Task.completed_at <= Task.scheduled_end,
                )
                .scalar()
                or 0
            )
            on_time_rate = round(on_time / completed * 100)

        # Domain time
        domain_stats = (
            self.db.query(Task.domain_id, func.sum(Task.duration_minutes))
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
                Task.status != "cancelled",
            )
            .group_by(Task.domain_id)
            .all()
        )
        domain_text = "\n".join(
            f"  Domain {d}: {m or 0} minutes"
            for d, m in domain_stats
        ) or "  No domain data"

        prompt = WEEKLY_SUMMARY_PROMPT.format(
            week_start=ws_date.isoformat(),
            week_end=we_date.isoformat(),
            completed_count=completed,
            on_time_rate=on_time_rate,
            domain_time=domain_text,
            streak=0,
        )

        try:
            return chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.5,
                max_tokens=4096,
            )
        except Exception:
            return f"This week: {completed} tasks completed out of {total} scheduled."

    def project_status(self, project_id: int) -> str:
        """Generate a project status update."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return "Project not found."

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
        pct = round(completed / total * 100) if total > 0 else 0

        recent = (
            self.db.query(Task)
            .filter(Task.project_id == project_id)
            .order_by(Task.updated_at.desc())
            .limit(5)
            .all()
        )
        recent_text = "\n".join(
            f"- {'✓' if t.status == 'completed' else '○'} {t.title}"
            for t in recent
        )

        prompt = PROJECT_STATUS_PROMPT.format(
            project_name=project.name,
            deadline=project.deadline or "No deadline",
            completion_pct=pct,
            completed_tasks=completed,
            total_tasks=total,
            at_risk="Yes" if pct < 50 and project.deadline else "No",
            recent_tasks=recent_text or "No tasks yet",
        )

        try:
            return chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.4,
                max_tokens=4096,
            )
        except Exception:
            return f"Project '{project.name}': {pct}% complete ({completed}/{total} tasks)."

    def tomorrow_briefing(self) -> str:
        """Generate a brief look-ahead for tomorrow."""
        tomorrow = date.today() + timedelta(days=1)
        ts = start_of_day(tomorrow).isoformat()
        te = end_of_day(tomorrow).isoformat()

        tasks = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ts,
                Task.scheduled_start <= te,
                Task.status.in_(["pending", "in_progress"]),
            )
            .order_by(Task.scheduled_start)
            .all()
        )

        if not tasks:
            return "Tomorrow is clear — no tasks scheduled."

        first = tasks[0]
        return f"Tomorrow: {len(tasks)} tasks scheduled, first at {first.scheduled_start}."
