"""Time parser — natural language time expressions to concrete datetimes."""

import re
from datetime import datetime, timedelta, time, timezone, date
from dataclasses import dataclass

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU


@dataclass
class TimeParse:
    resolved_start: datetime | None
    resolved_end: datetime | None
    is_flexible: bool
    confidence: float
    original_expression: str


# Day-of-week mappings
_WEEKDAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_RELATIVE_DAY_MAP = {
    MO: 0, TU: 1, WE: 2, TH: 3, FR: 4, SA: 5, SU: 6,
}

_TIME_OF_DAY = {
    "morning": (9, 0),
    "afternoon": (14, 0),
    "evening": (18, 0),
    "night": (20, 0),
    "noon": (12, 0),
    "midnight": (0, 0),
    "lunch": (12, 0),
    "lunchtime": (12, 0),
    "eod": (17, 0),
    "end of day": (17, 0),
}


class TimeParser:
    """Resolves natural language time expressions to concrete datetimes."""

    def parse(
        self,
        expression: str,
        reference_time: datetime | None = None,
        default_duration: int = 60,
    ) -> TimeParse:
        if not expression or not expression.strip():
            return TimeParse(None, None, True, 0.0, expression or "")

        ref = reference_time or datetime.now(timezone.utc)
        expr = expression.strip().lower()

        # Try patterns in order of specificity
        for parser_fn in [
            self._parse_relative_days,
            self._parse_next_weekday,
            self._parse_in_duration,
            self._parse_time_of_day,
            self._parse_vague_period,
            self._parse_dateutil,
        ]:
            result = parser_fn(expr, ref, default_duration)
            if result is not None:
                return result

        # Could not parse → flexible task
        return TimeParse(
            resolved_start=None,
            resolved_end=None,
            is_flexible=True,
            confidence=0.1,
            original_expression=expression,
        )

    def _parse_relative_days(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Handle 'today', 'tomorrow', 'day after tomorrow'."""
        today = ref.date()

        day_offset = None
        time_part = None

        if expr.startswith("today"):
            day_offset = 0
            time_part = expr.replace("today", "").strip()
        elif expr.startswith("tomorrow"):
            day_offset = 1
            time_part = expr.replace("tomorrow", "").strip()
        elif "day after tomorrow" in expr:
            day_offset = 2
            time_part = expr.replace("day after tomorrow", "").strip()
        elif expr.startswith("yesterday"):
            day_offset = -1
            time_part = expr.replace("yesterday", "").strip()

        if day_offset is None:
            return None

        target_date = today + timedelta(days=day_offset)

        # Extract time if present
        hour, minute = self._extract_time(time_part)

        if hour is not None:
            start = datetime.combine(target_date, time(hour, minute), tzinfo=timezone.utc)
            return TimeParse(
                resolved_start=start,
                resolved_end=start + timedelta(minutes=duration),
                is_flexible=False,
                confidence=0.9,
                original_expression=expr,
            )

        # Date known but no time → flexible within that day
        start = datetime.combine(target_date, time(9, 0), tzinfo=timezone.utc)
        return TimeParse(
            resolved_start=start,
            resolved_end=start + timedelta(minutes=duration),
            is_flexible=True,
            confidence=0.6,
            original_expression=expr,
        )

    def _parse_next_weekday(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Handle 'next Friday', 'this Monday', 'on Wednesday'."""
        for prefix in ["next ", "this ", "on ", ""]:
            for day_name, day_num in _WEEKDAY_MAP.items():
                pattern = prefix + day_name
                if expr.startswith(pattern):
                    time_part = expr[len(pattern):].strip()
                    today_weekday = ref.weekday()

                    if prefix == "next ":
                        days_ahead = (day_num - today_weekday + 7) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                    else:
                        days_ahead = (day_num - today_weekday + 7) % 7
                        if days_ahead == 0:
                            days_ahead = 7

                    target_date = ref.date() + timedelta(days=days_ahead)
                    hour, minute = self._extract_time(time_part)

                    if hour is not None:
                        start = datetime.combine(target_date, time(hour, minute), tzinfo=timezone.utc)
                        return TimeParse(start, start + timedelta(minutes=duration), False, 0.85, expr)

                    start = datetime.combine(target_date, time(9, 0), tzinfo=timezone.utc)
                    return TimeParse(start, start + timedelta(minutes=duration), True, 0.6, expr)

        return None

    def _parse_in_duration(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Handle 'in 2 hours', 'in 30 minutes', 'in 3 days'."""
        match = re.match(r"in\s+(\d+)\s+(hour|hr|minute|min|day|week)s?", expr)
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)

        if unit in ("hour", "hr"):
            delta = timedelta(hours=amount)
        elif unit in ("minute", "min"):
            delta = timedelta(minutes=amount)
        elif unit == "day":
            delta = timedelta(days=amount)
        elif unit == "week":
            delta = timedelta(weeks=amount)
        else:
            return None

        start = ref + delta
        return TimeParse(start, start + timedelta(minutes=duration), False, 0.9, expr)

    def _parse_time_of_day(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Handle 'morning', 'afternoon', 'evening', 'noon'."""
        for period, (hour, minute) in _TIME_OF_DAY.items():
            if expr == period or expr == f"this {period}":
                start = datetime.combine(ref.date(), time(hour, minute), tzinfo=timezone.utc)
                if start < ref:
                    start += timedelta(days=1)
                return TimeParse(start, start + timedelta(minutes=duration), True, 0.5, expr)
        return None

    def _parse_vague_period(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Handle 'sometime next week', 'end of this month', etc."""
        if "next week" in expr:
            next_monday = ref.date() + timedelta(days=(7 - ref.weekday()))
            start = datetime.combine(next_monday, time(9, 0), tzinfo=timezone.utc)
            return TimeParse(start, start + timedelta(minutes=duration), True, 0.3, expr)

        if "this week" in expr:
            start = datetime.combine(ref.date(), time(9, 0), tzinfo=timezone.utc)
            return TimeParse(start, start + timedelta(minutes=duration), True, 0.3, expr)

        if "end of" in expr and "month" in expr:
            last_day = (ref.date().replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            start = datetime.combine(last_day, time(9, 0), tzinfo=timezone.utc)
            return TimeParse(start, start + timedelta(minutes=duration), True, 0.3, expr)

        if "end of" in expr and "week" in expr:
            friday = ref.date() + timedelta(days=(4 - ref.weekday()) % 7)
            if friday <= ref.date():
                friday += timedelta(days=7)
            start = datetime.combine(friday, time(9, 0), tzinfo=timezone.utc)
            return TimeParse(start, start + timedelta(minutes=duration), True, 0.3, expr)

        return None

    def _parse_dateutil(
        self, expr: str, ref: datetime, duration: int
    ) -> TimeParse | None:
        """Fallback to python-dateutil for specific date/time parsing."""
        # Strip common prefixes
        cleaned = re.sub(r"^(at|on|by|before|after|around)\s+", "", expr)

        try:
            parsed = dateutil_parser.parse(cleaned, default=ref, fuzzy=True)

            # If only time was parsed (date matches ref), check if it's past
            if parsed.date() == ref.date() and parsed < ref:
                parsed += timedelta(days=1)

            return TimeParse(
                resolved_start=parsed.replace(tzinfo=timezone.utc),
                resolved_end=(parsed + timedelta(minutes=duration)).replace(tzinfo=timezone.utc),
                is_flexible=False,
                confidence=0.7,
                original_expression=expr,
            )
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def _extract_time(text: str) -> tuple[int | None, int]:
        """Extract hour and minute from a time string fragment."""
        if not text:
            return None, 0

        text = text.strip().lstrip("at ").strip()

        # Check time-of-day keywords
        for period, (hour, minute) in _TIME_OF_DAY.items():
            if period in text:
                return hour, minute

        # Try "3pm", "3:30pm", "15:00", etc.
        match = re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", text, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            meridiem = (match.group(3) or "").lower()

            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute

        return None, 0
