"""Unit tests for TimeParser."""

from datetime import datetime, timezone, timedelta

import pytest

from app.ai.time_parser import TimeParser


@pytest.fixture()
def parser():
    return TimeParser()


@pytest.fixture()
def ref():
    """Monday 2025-06-09 10:00 UTC."""
    return datetime(2025, 6, 9, 10, 0, 0, tzinfo=timezone.utc)


class TestRelativeDays:
    def test_today(self, parser, ref):
        result = parser.parse("today", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.date() == ref.date()
        assert result.confidence >= 0.5

    def test_today_at_3pm(self, parser, ref):
        result = parser.parse("today at 3pm", ref)
        assert result.resolved_start.hour == 15
        assert result.is_flexible is False
        assert result.confidence >= 0.8

    def test_tomorrow(self, parser, ref):
        result = parser.parse("tomorrow", ref)
        assert result.resolved_start.date() == ref.date() + timedelta(days=1)

    def test_tomorrow_morning(self, parser, ref):
        result = parser.parse("tomorrow morning", ref)
        assert result.resolved_start.date() == ref.date() + timedelta(days=1)
        assert result.resolved_start.hour == 9

    def test_day_after_tomorrow(self, parser, ref):
        result = parser.parse("day after tomorrow", ref)
        assert result.resolved_start.date() == ref.date() + timedelta(days=2)


class TestNextWeekday:
    def test_next_friday(self, parser, ref):
        # ref is Monday, next friday is +4 days
        result = parser.parse("next friday", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.weekday() == 4  # Friday

    def test_next_monday(self, parser, ref):
        # ref is Monday, next monday is +7 days
        result = parser.parse("next monday", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.weekday() == 0
        assert result.resolved_start.date() > ref.date()

    def test_next_wednesday_at_2pm(self, parser, ref):
        result = parser.parse("next wednesday at 2pm", ref)
        assert result.resolved_start.weekday() == 2
        assert result.resolved_start.hour == 14
        assert result.is_flexible is False


class TestInDuration:
    def test_in_2_hours(self, parser, ref):
        result = parser.parse("in 2 hours", ref)
        expected = ref + timedelta(hours=2)
        assert result.resolved_start == expected
        assert result.confidence >= 0.8

    def test_in_30_minutes(self, parser, ref):
        result = parser.parse("in 30 minutes", ref)
        expected = ref + timedelta(minutes=30)
        assert result.resolved_start == expected

    def test_in_3_days(self, parser, ref):
        result = parser.parse("in 3 days", ref)
        expected = ref + timedelta(days=3)
        assert result.resolved_start == expected

    def test_in_1_week(self, parser, ref):
        result = parser.parse("in 1 week", ref)
        expected = ref + timedelta(weeks=1)
        assert result.resolved_start == expected


class TestTimeOfDay:
    def test_morning(self, parser, ref):
        result = parser.parse("morning", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.hour == 9
        assert result.is_flexible is True

    def test_afternoon(self, parser, ref):
        result = parser.parse("afternoon", ref)
        assert result.resolved_start.hour == 14

    def test_noon(self, parser, ref):
        result = parser.parse("noon", ref)
        assert result.resolved_start.hour == 12


class TestVaguePeriod:
    def test_next_week(self, parser, ref):
        result = parser.parse("next week", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.weekday() == 0  # Monday
        assert result.resolved_start.date() > ref.date()
        assert result.is_flexible is True
        assert result.confidence <= 0.5

    def test_end_of_week(self, parser, ref):
        result = parser.parse("end of week", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.weekday() == 4  # Friday

    def test_end_of_month(self, parser, ref):
        result = parser.parse("end of month", ref)
        assert result.resolved_start is not None
        assert result.resolved_start.day >= 28


class TestDuration:
    def test_default_duration_applied(self, parser, ref):
        result = parser.parse("tomorrow", ref, default_duration=90)
        delta = (result.resolved_end - result.resolved_start).total_seconds() / 60
        assert delta == 90


class TestEdgeCases:
    def test_empty_string(self, parser, ref):
        result = parser.parse("", ref)
        assert result.resolved_start is None
        assert result.is_flexible is True
        assert result.confidence < 0.2

    def test_unparseable(self, parser, ref):
        result = parser.parse("qwerty asdf zxcv", ref)
        assert result.is_flexible is True
        assert result.confidence <= 0.5
