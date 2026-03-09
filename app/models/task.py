"""Task model — core scheduling entity."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("domains.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(
        String, nullable=False, default="medium"
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_flexible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    domain = relationship("Domain", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("Task", remote_side="Task.id", backref="subtasks")
    reminders = relationship("Reminder", back_populates="task", cascade="all, delete-orphan")
    recurrence_exceptions = relationship(
        "TaskRecurrenceException", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_tasks_scheduled_start", "scheduled_start"),
        Index("idx_tasks_domain_id", "domain_id"),
        Index("idx_tasks_project_id", "project_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_is_flexible", "is_flexible"),
    )


class TaskRecurrenceException(Base):
    __tablename__ = "task_recurrence_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    original_date: Mapped[str] = mapped_column(String, nullable=False)
    new_start: Mapped[str | None] = mapped_column(String, nullable=True)
    new_end: Mapped[str | None] = mapped_column(String, nullable=True)
    new_title: Mapped[str | None] = mapped_column(String, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    task = relationship("Task", back_populates="recurrence_exceptions")
