"""Initial schema.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- domains ---
    op.create_table(
        "domains",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("color", sa.String, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("deadline", sa.DateTime, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("domain_id", sa.Integer, sa.ForeignKey("domains.id"), nullable=True),
        sa.Column("priority", sa.String, nullable=False, server_default="medium"),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("scheduled_start", sa.DateTime, nullable=True),
        sa.Column("scheduled_end", sa.DateTime, nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("is_flexible", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("recurrence_rule", sa.Text, nullable=True),
        sa.Column("parent_task_id", sa.Integer, sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_tasks_scheduled_start", "tasks", ["scheduled_start"])
    op.create_index("idx_tasks_domain_id", "tasks", ["domain_id"])
    op.create_index("idx_tasks_project_id", "tasks", ["project_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_is_flexible", "tasks", ["is_flexible"])

    # --- task_recurrence_exceptions ---
    op.create_table(
        "task_recurrence_exceptions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.Integer,
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_date", sa.String, nullable=False),
        sa.Column("new_start", sa.String, nullable=True),
        sa.Column("new_end", sa.String, nullable=True),
        sa.Column("new_title", sa.String, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # --- milestones ---
    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("target_date", sa.DateTime, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # --- reminders ---
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.Integer,
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reminder_type", sa.String, nullable=False),
        sa.Column("trigger_at", sa.DateTime, nullable=False),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("recurrence_rule", sa.Text, nullable=True),
        sa.Column("is_fired", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_dismissed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("snoozed_until", sa.DateTime, nullable=True),
        sa.Column("notification_id", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_reminders_trigger_at", "reminders", ["trigger_at"])
    op.create_index("idx_reminders_task_id", "reminders", ["task_id"])

    # --- user_settings ---
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer, primary_key=True, default=1),
        sa.Column("work_start_hour", sa.Integer, nullable=False, server_default="9"),
        sa.Column("work_end_hour", sa.Integer, nullable=False, server_default="17"),
        sa.Column("work_days", sa.String, nullable=False, server_default="[1,2,3,4,5]"),
        sa.Column("default_duration_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("default_reminder_lead_minutes", sa.Integer, nullable=False, server_default="15"),
        sa.Column("daily_task_limit_hours", sa.Float, nullable=False, server_default="8.0"),
        sa.Column("buffer_minutes", sa.Integer, nullable=False, server_default="10"),
        sa.Column("weekend_mode", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("theme", sa.String, nullable=False, server_default="dark"),
        sa.Column("selected_model", sa.String, nullable=False, server_default="gpt-oss-20b"),
        sa.Column("nudge_preferences", sa.Text, nullable=False, server_default="{}"),
        sa.Column("auto_backup_enabled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("auto_backup_interval_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("auto_backup_path", sa.String, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("id = 1", name="single_row_settings"),
    )

    # --- backup_log ---
    op.create_table(
        "backup_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("backup_path", sa.String, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # --- FTS5 virtual table for full-text search ---
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
            title,
            description,
            content='tasks',
            content_rowid='id',
            tokenize='porter'
        )
    """)

    # --- Triggers to keep FTS index in sync ---
    op.execute("""
        CREATE TRIGGER tasks_ai AFTER INSERT ON tasks BEGIN
            INSERT INTO tasks_fts(rowid, title, description)
            VALUES (new.id, new.title, new.description);
        END
    """)

    op.execute("""
        CREATE TRIGGER tasks_ad AFTER DELETE ON tasks BEGIN
            INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
            VALUES ('delete', old.id, old.title, old.description);
        END
    """)

    op.execute("""
        CREATE TRIGGER tasks_au AFTER UPDATE ON tasks BEGIN
            INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
            VALUES ('delete', old.id, old.title, old.description);
            INSERT INTO tasks_fts(rowid, title, description)
            VALUES (new.id, new.title, new.description);
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tasks_au")
    op.execute("DROP TRIGGER IF EXISTS tasks_ad")
    op.execute("DROP TRIGGER IF EXISTS tasks_ai")
    op.execute("DROP TABLE IF EXISTS tasks_fts")
    op.drop_table("backup_log")
    op.drop_table("user_settings")
    op.drop_table("reminders")
    op.drop_table("milestones")
    op.drop_table("task_recurrence_exceptions")
    op.drop_table("tasks")
    op.drop_table("projects")
    op.drop_table("domains")
