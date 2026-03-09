"""Datetime helper utilities."""

from datetime import datetime, date, time, timedelta, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def end_of_day(d: date) -> datetime:
    return datetime.combine(d, time.max)


def start_of_week(d: date) -> date:
    """Return Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


def end_of_week(d: date) -> date:
    """Return Sunday of the week containing `d`."""
    return d + timedelta(days=6 - d.weekday())


def time_ranges_overlap(
    start1: datetime, end1: datetime,
    start2: datetime, end2: datetime,
) -> bool:
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1


def minutes_between(start: datetime, end: datetime) -> int:
    """Return the number of minutes between two datetimes."""
    delta = end - start
    return int(delta.total_seconds() / 60)
