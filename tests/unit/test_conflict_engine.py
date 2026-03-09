"""Unit tests for ConflictEngine."""

from datetime import datetime, timezone, timedelta

import pytest

from app.models.task import Task
from app.services.conflict_engine import ConflictEngine


def _make_task(
    id_: int,
    title: str,
    start_hour: int,
    end_hour: int,
    date: datetime | None = None,
) -> Task:
    """Helper to create a mock Task object."""
    base = date or datetime(2025, 6, 9, tzinfo=timezone.utc)
    t = Task()
    t.id = id_
    t.title = title
    t.scheduled_start = base.replace(hour=start_hour)
    t.scheduled_end = base.replace(hour=end_hour)
    t.duration_minutes = (end_hour - start_hour) * 60
    return t


class TestCheckConflicts:
    def test_no_conflicts_when_no_overlap(self):
        engine = ConflictEngine(buffer_minutes=10)
        new = _make_task(1, "New Task", 14, 15)
        existing = [_make_task(2, "Morning", 9, 10)]
        assert engine.check_conflicts(new, existing) == []

    def test_detects_time_overlap(self):
        engine = ConflictEngine(buffer_minutes=0)
        new = _make_task(1, "New Task", 9, 11)
        existing = [_make_task(2, "Existing", 10, 12)]
        conflicts = engine.check_conflicts(new, existing)
        assert len(conflicts) == 1
        assert conflicts[0].type == "TIME_OVERLAP"
        assert conflicts[0].severity == "high"

    def test_detects_no_buffer(self):
        engine = ConflictEngine(buffer_minutes=15)
        new = _make_task(1, "New Task", 10, 11)
        existing = [_make_task(2, "Existing", 11, 12)]
        conflicts = engine.check_conflicts(new, existing)
        types = [c.type for c in conflicts]
        assert "NO_BUFFER" in types

    def test_no_buffer_conflict_with_zero_buffer(self):
        engine = ConflictEngine(buffer_minutes=0)
        new = _make_task(1, "New Task", 10, 11)
        existing = [_make_task(2, "Existing", 11, 12)]
        conflicts = engine.check_conflicts(new, existing)
        assert all(c.type != "NO_BUFFER" for c in conflicts)

    def test_detects_daily_overload(self):
        engine = ConflictEngine(buffer_minutes=0, daily_limit_hours=4.0)
        new = _make_task(1, "New Task", 15, 17)
        existing = [
            _make_task(2, "A", 9, 12),  # 3h
        ]
        # new is 2h + existing 3h = 5h > 4h limit
        conflicts = engine.check_conflicts(new, existing)
        types = [c.type for c in conflicts]
        assert "DAILY_OVERLOAD" in types

    def test_skips_task_against_itself(self):
        engine = ConflictEngine()
        new = _make_task(1, "Self", 9, 10)
        existing = [_make_task(1, "Self", 9, 10)]
        conflicts = engine.check_conflicts(new, existing)
        assert len(conflicts) == 0

    def test_no_conflict_for_unscheduled_task(self):
        engine = ConflictEngine()
        new = Task()
        new.id = 1
        new.title = "Unscheduled"
        new.scheduled_start = None
        new.scheduled_end = None
        existing = [_make_task(2, "Existing", 9, 10)]
        assert engine.check_conflicts(new, existing) == []


class TestGenerateResolutions:
    def test_always_includes_keep_anyway(self):
        engine = ConflictEngine()
        new = _make_task(1, "New", 9, 10)
        existing = [_make_task(2, "Existing", 9, 10)]
        conflicts = engine.check_conflicts(new, existing)
        resolutions = engine.generate_resolutions(conflicts[0], new, existing)
        ids = [r.id for r in resolutions]
        assert "keep_anyway" in ids

    def test_offers_move_same_day(self):
        engine = ConflictEngine(buffer_minutes=0)
        new = _make_task(1, "New", 9, 10)
        existing = [_make_task(2, "Existing", 9, 10)]
        conflicts = engine.check_conflicts(new, existing)
        resolutions = engine.generate_resolutions(conflicts[0], new, existing)
        ids = [r.id for r in resolutions]
        assert "move_same_day" in ids

    def test_offers_push_tomorrow(self):
        engine = ConflictEngine(buffer_minutes=0)
        new = _make_task(1, "New", 9, 10)
        existing = [_make_task(2, "Existing", 9, 10)]
        conflicts = engine.check_conflicts(new, existing)
        resolutions = engine.generate_resolutions(conflicts[0], new, existing)
        ids = [r.id for r in resolutions]
        assert "push_tomorrow" in ids


class TestFindNextFreeSlot:
    def test_finds_first_gap(self):
        engine = ConflictEngine(buffer_minutes=0)
        date = datetime(2025, 6, 9, tzinfo=timezone.utc).date()
        existing = [_make_task(1, "A", 9, 10), _make_task(2, "B", 11, 12)]
        slot = engine.find_next_free_slot(60, date, existing, start_hour=9)
        assert slot is not None
        assert slot.hour == 10  # gap between A(10) and B(11)

    def test_returns_none_when_no_space(self):
        engine = ConflictEngine(buffer_minutes=0)
        date = datetime(2025, 6, 9, tzinfo=timezone.utc).date()
        # Pack the day full
        existing = [_make_task(i, f"T{i}", h, h + 1) for i, h in enumerate(range(6, 23), 1)]
        slot = engine.find_next_free_slot(120, date, existing, start_hour=6, end_hour=23)
        assert slot is None


class TestDailyLoad:
    def test_calculates_load(self):
        engine = ConflictEngine()
        date = datetime(2025, 6, 9, tzinfo=timezone.utc).date()
        tasks = [_make_task(1, "A", 9, 11), _make_task(2, "B", 14, 16)]
        load = engine.calculate_daily_load(date, tasks)
        assert load.total_minutes == 240
        assert load.task_count == 2
        assert load.is_overloaded is False

    def test_overloaded_day(self):
        engine = ConflictEngine(daily_limit_hours=4.0)
        date = datetime(2025, 6, 9, tzinfo=timezone.utc).date()
        tasks = [_make_task(1, "A", 8, 12), _make_task(2, "B", 13, 18)]
        load = engine.calculate_daily_load(date, tasks)
        assert load.is_overloaded is True
