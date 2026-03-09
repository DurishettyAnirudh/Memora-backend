"""Unit tests for TaskService."""

from datetime import datetime, timezone, timedelta

import pytest

from app.models.task import Task
from app.models.domain import Domain
from app.schemas.task import TaskCreate, TaskUpdate, BulkOperation
from app.services.task_service import TaskService


@pytest.fixture()
def task_service(db):
    return TaskService(db)


@pytest.fixture()
def sample_domain(db):
    domain = Domain(name="Work", color="#B0C4DE", sort_order=0)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


class TestCreateTask:
    def test_creates_task(self, task_service, sample_domain):
        data = TaskCreate(
            title="Test task",
            domain_id=sample_domain.id,
            priority="high",
        )
        task = task_service.create_task(data)
        assert task.id is not None
        assert task.title == "Test task"
        assert task.priority == "high"

    def test_auto_computes_end(self, task_service):
        start = datetime(2025, 6, 9, 10, 0, tzinfo=timezone.utc)
        data = TaskCreate(
            title="Timed task",
            scheduled_start=start,
            duration_minutes=30,
        )
        task = task_service.create_task(data)
        assert task.scheduled_end == start + timedelta(minutes=30)


class TestGetTask:
    def test_get_existing(self, task_service):
        data = TaskCreate(title="Find me")
        task = task_service.create_task(data)
        found = task_service.get_task(task.id)
        assert found is not None
        assert found.title == "Find me"

    def test_get_nonexistent(self, task_service):
        assert task_service.get_task(99999) is None


class TestUpdateTask:
    def test_updates_fields(self, task_service):
        task = task_service.create_task(TaskCreate(title="Original"))
        updated = task_service.update_task(task.id, TaskUpdate(title="Changed"))
        assert updated.title == "Changed"

    def test_update_nonexistent(self, task_service):
        assert task_service.update_task(99999, TaskUpdate(title="X")) is None

    def test_recomputes_end_on_duration_change(self, task_service):
        start = datetime(2025, 6, 9, 10, 0, tzinfo=timezone.utc)
        task = task_service.create_task(
            TaskCreate(title="T", scheduled_start=start, duration_minutes=30)
        )
        updated = task_service.update_task(task.id, TaskUpdate(duration_minutes=90))
        assert updated.scheduled_end == start + timedelta(minutes=90)


class TestDeleteTask:
    def test_deletes_task(self, task_service):
        task = task_service.create_task(TaskCreate(title="Delete me"))
        assert task_service.delete_task(task.id) is True
        assert task_service.get_task(task.id) is None

    def test_delete_nonexistent(self, task_service):
        assert task_service.delete_task(99999) is False


class TestCompleteTask:
    def test_marks_completed(self, task_service):
        task = task_service.create_task(TaskCreate(title="Complete me"))
        completed = task_service.complete_task(task.id)
        assert completed.status == "completed"
        assert completed.completed_at is not None


class TestInbox:
    def test_inbox_returns_flexible_pending(self, task_service):
        task_service.create_task(TaskCreate(title="Flex", is_flexible=True))
        task_service.create_task(
            TaskCreate(
                title="Scheduled",
                scheduled_start=datetime(2025, 6, 9, 10, 0, tzinfo=timezone.utc),
                is_flexible=False,
            )
        )
        inbox = task_service.get_inbox()
        assert len(inbox) == 1
        assert inbox[0].title == "Flex"

    def test_inbox_count(self, task_service):
        task_service.create_task(TaskCreate(title="A", is_flexible=True))
        task_service.create_task(TaskCreate(title="B", is_flexible=True))
        assert task_service.get_inbox_count() == 2


class TestListTasks:
    def test_filter_by_status(self, task_service):
        task_service.create_task(TaskCreate(title="Pending"))
        t = task_service.create_task(TaskCreate(title="Done"))
        task_service.complete_task(t.id)
        pending = task_service.list_tasks(status="pending")
        assert all(t.status == "pending" for t in pending)

    def test_filter_by_domain(self, task_service, sample_domain):
        task_service.create_task(TaskCreate(title="Work", domain_id=sample_domain.id))
        task_service.create_task(TaskCreate(title="No domain"))
        result = task_service.list_tasks(domain_id=sample_domain.id)
        assert len(result) == 1
        assert result[0].title == "Work"


class TestBulkOperation:
    def test_bulk_complete(self, task_service):
        t1 = task_service.create_task(TaskCreate(title="A"))
        t2 = task_service.create_task(TaskCreate(title="B"))
        result = task_service.bulk_operation(
            BulkOperation(task_ids=[t1.id, t2.id], operation="complete_all")
        )
        assert result.affected == 2
