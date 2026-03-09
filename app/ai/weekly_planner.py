"""Weekly planner — guided conversational flow for weekly planning."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.ai.client import chat_completion
from app.ai.prompts.weekly_planner import WEEKLY_REVIEW_PROMPT, WEEKLY_BALANCE_PROMPT
from app.models.task import Task
from app.utils.datetime_helpers import start_of_week, end_of_week, start_of_day, end_of_day


STAGES = ["review", "carry_forward", "new_goals", "balance_check", "confirm"]


class WeeklyPlanner:
    """Guided conversational flow for weekly planning."""

    def __init__(self, db: Session):
        self.db = db

    def start_planning(self, session_id: str) -> dict:
        """Stage 1: Show what's already scheduled for the week."""
        today = date.today()
        week_start = start_of_week(today)
        week_end = end_of_week(today)

        # Get current week's tasks
        ws = start_of_day(week_start).isoformat()
        we = end_of_day(week_end).isoformat()

        scheduled = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
                Task.status != "cancelled",
            )
            .order_by(Task.scheduled_start)
            .all()
        )

        # Get incomplete tasks from last week
        last_week_start = week_start - timedelta(days=7)
        lws = start_of_day(last_week_start).isoformat()

        incomplete = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= lws,
                Task.scheduled_start < ws,
                Task.status == "pending",
            )
            .order_by(Task.scheduled_start)
            .all()
        )

        schedule_text = "\n".join(
            f"- {t.title} ({t.scheduled_start})" for t in scheduled
        ) or "Nothing scheduled yet."

        incomplete_text = "\n".join(
            f"- {t.title} (was {t.scheduled_start})" for t in incomplete
        ) or "All caught up!"

        prompt = WEEKLY_REVIEW_PROMPT.format(
            current_schedule=schedule_text,
            incomplete_tasks=incomplete_text,
        )

        try:
            review = chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.4,
                max_tokens=4096,
            )
        except Exception:
            review = f"This week you have {len(scheduled)} tasks scheduled. {len(incomplete)} tasks from last week are incomplete."

        return {
            "stage": "review",
            "message": review,
            "scheduled_count": len(scheduled),
            "incomplete_count": len(incomplete),
            "incomplete_tasks": [
                {"id": t.id, "title": t.title, "original_date": t.scheduled_start}
                for t in incomplete
            ],
        }

    def check_balance(self) -> dict:
        """Stage 4: Analyze the resulting schedule for balance."""
        today = date.today()
        week_start = start_of_week(today)
        week_end = end_of_week(today)
        ws = start_of_day(week_start).isoformat()
        we = end_of_day(week_end).isoformat()

        tasks = (
            self.db.query(Task)
            .filter(
                Task.scheduled_start.isnot(None),
                Task.scheduled_start >= ws,
                Task.scheduled_start <= we,
                Task.status != "cancelled",
            )
            .order_by(Task.scheduled_start)
            .all()
        )

        schedule_text = "\n".join(
            f"- {t.title} ({t.scheduled_start}, {t.duration_minutes}min, domain:{t.domain_id})"
            for t in tasks
        ) or "No tasks scheduled."

        prompt = WEEKLY_BALANCE_PROMPT.format(
            schedule=schedule_text,
            work_start=9,
            work_end=17,
            daily_limit=8,
            work_days="Mon-Fri",
        )

        try:
            analysis = chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.4,
                max_tokens=4096,
            )
        except Exception:
            analysis = f"You have {len(tasks)} tasks this week."

        return {
            "stage": "balance_check",
            "message": analysis,
            "task_count": len(tasks),
        }
