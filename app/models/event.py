"""CalendarEvent model — virtual view model, not stored separately."""

# Calendar events are derived from Task records.
# This module provides the CalendarEvent dataclass used for API responses.
# No ORM model needed — calendar queries are projections from the tasks table.
