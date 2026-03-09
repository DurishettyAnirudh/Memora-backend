"""Chat service — single-call AI agent that talks naturally and executes actions."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai.client import chat_completion_with_memori
from app.ai.time_parser import TimeParser
from app.ai.validators import parse_llm_json
from app.models.task import Task
from app.models.domain import Domain
from app.models.reminder import Reminder
from app.schemas.task import TaskCreate
from app.schemas.chat import (
    ChatResponse,
    HistoryMessage,
    LiveContext,
    SystemEvent,
)
from app.services.task_service import TaskService
from app.services.notification_client import NotificationClient
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """\
You are **Memora**, a smart personal scheduling assistant. You talk naturally, \
warmly, and concisely — like a helpful human assistant, not a robot.

## Current date/time
{now}

## User's existing tasks
{task_context}

## Available life domains
{domains}

## What you can do
Respond with a JSON object containing TWO keys:
1. "reply" — your natural language response to the user. Be friendly, concise, specific.
2. "actions" — a list of actions to execute (can be empty []).

### Supported actions
Each action is an object with an "action" key and relevant data:

**create_task**: Create a new task.
```json
{{"action": "create_task", "title": "...", "scheduled_start": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": 60, "domain_id": 1, "priority": "medium", "remind_before_minutes": 15, "notify_message": "..."}}
```
- scheduled_start can be null for inbox/unscheduled tasks.
- domain_id: {domain_map}
- priority: "high", "medium", or "low"
- remind_before_minutes: how many minutes before scheduled_start to send the reminder. Default 15.
  - If user says "remind me IN X minutes/hours" (e.g. "remind me in 2 minutes") → set scheduled_start = now + X, remind_before_minutes = 0 (fire AT the scheduled time).
  - If user says "remind me X before" (e.g. "remind me an hour before the meeting") → set remind_before_minutes to that offset (60).
  - "a day before" = 1440, "an hour before" = 60, "30 min before" = 30.
- notify_message: a short, friendly, context-aware reminder message to send via Telegram. Use what you know about the task — be specific and motivating. E.g. "Don't forget: your gym session starts in 15 minutes. Get your gear ready!" or "Good morning! Time to check your emails as scheduled."

**delete_task**: Delete one or more tasks by ID.
```json
{{"action": "delete_task", "task_ids": [1, 2, 3]}}
```

**complete_task**: Mark task(s) as completed.
```json
{{"action": "complete_task", "task_ids": [1]}}
```

**update_task**: Update a task.
```json
{{"action": "update_task", "task_id": 1, "title": "...", "scheduled_start": "...", "priority": "..."}}
```

## Rules
1. ALWAYS respond with valid JSON: {{"reply": "...", "actions": [...]}}
2. For greetings like "Hello", "Hi", "Hey" — reply with a short friendly greeting. Do NOT list tasks unless the user asks. Example: {{"reply": "Hey! How can I help you today?", "actions": []}}
3. For chitchat, jokes, or questions unrelated to tasks — just have a normal conversation with actions=[].
4. ONLY show the task list when the user explicitly asks about their tasks, schedule, or what they have to do.
5. When the user says "delete all tasks" or "clear everything" — include ALL task IDs in a single delete_task action.
6. For "delete <task name>" — find the matching task(s) by title from the list and delete by ID. Be fuzzy — "gym workout" matches "Gym workout".
7. When creating tasks, use the current date context to resolve "tomorrow", "next Monday", etc. into actual ISO datetime strings.
8. If the user references a previous message (like "yes that one", "delete it"), use the conversation history for context.
9. Never hallucinate tasks that don't exist. Only reference tasks from the list above.
10. Keep replies SHORT — 1-2 sentences max unless the user asks for detail.
11. NEVER wrap the JSON in markdown code fences. Return raw JSON only.
"""


class ChatService:
    """AI agent that handles the full chat flow with a single LLM call."""

    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
        self.time_parser = TimeParser()
        self._notif_client = NotificationClient()

    async def handle_message(
        self,
        message: str,
        session_id: str | None = None,
        history: list[HistoryMessage] | None = None,
        utc_offset_minutes: int = 0,
    ) -> ChatResponse:
        if not session_id:
            session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        self._utc_offset_minutes = utc_offset_minutes

        # Gather context
        now = datetime.now(timezone.utc)
        tasks = (
            self.db.query(Task)
            .filter(Task.status.in_(["pending", "in_progress"]))
            .order_by(Task.scheduled_start.asc().nullslast())
            .all()
        )
        domains = (
            self.db.query(Domain)
            .filter(Domain.is_archived == False)  # noqa: E712
            .all()
        )

        task_context = self._format_tasks(tasks) if tasks else "No tasks yet."
        domain_names = ", ".join(f"{d.name} (id={d.id})" for d in domains)
        domain_map = ", ".join(f"{d.id}={d.name}" for d in domains)

        # Show the LLM the user's local time so it resolves "tomorrow", "midnight" etc correctly
        local_now = now + timedelta(minutes=utc_offset_minutes)
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            now=local_now.strftime("%Y-%m-%d %H:%M %A"),
            task_context=task_context,
            domains=domain_names,
            domain_map=domain_map,
        )

        # Build conversation history for context
        history_block = ""
        if history:
            lines = []
            for msg in history[-10:]:
                lines.append(f"{msg.role}: {msg.content}")
            history_block = (
                "\n\n## Recent conversation\n"
                + "\n".join(lines)
                + "\n\n## Current message\n"
            )

        user_content = history_block + message

        # Single LLM call
        raw = chat_completion_with_memori(
            user_message=user_content,
            system_prompt=system_prompt,
            session_id=session_id,
            temperature=0.4,
            max_tokens=4096,
        )

        logger.info("Agent raw response: %s", raw[:500] if raw else "(empty)")

        # Parse the JSON response
        parsed = parse_llm_json(raw)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("Failed to parse agent JSON, using raw as reply")
            return ChatResponse(
                reply=raw.strip() if raw else "Sorry, I had trouble processing that. Could you try again?",
                session_id=session_id,
            )

        reply = parsed.get("reply", "Done.")
        actions = parsed.get("actions", [])

        # Execute actions
        events: list[SystemEvent] = []
        for action_data in actions:
            action_events = await self._execute_action(action_data)
            events.extend(action_events)

        live_context = self._build_live_context(events)

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            events=events,
            live_context=live_context,
            requires_confirmation=False,
            confirmation_options=[],
        )

    async def handle_confirmation(
        self, session_id: str, option_id: str
    ) -> ChatResponse:
        return ChatResponse(
            reply=f"Got it! Applied option '{option_id}'.",
            session_id=session_id,
        )

    # ── Action execution ──────────────────────────────────────────────

    async def _execute_action(self, action_data: dict) -> list[SystemEvent]:
        action = action_data.get("action", "")
        if action == "create_task":
            return await self._action_create_task(action_data)
        elif action == "delete_task":
            return self._action_delete_tasks(action_data)
        elif action == "complete_task":
            return self._action_complete_tasks(action_data)
        elif action == "update_task":
            return self._action_update_task(action_data)
        return []

    async def _action_create_task(self, data: dict) -> list[SystemEvent]:
        title = data.get("title", "Untitled task")
        scheduled_start = None
        if data.get("scheduled_start"):
            try:
                scheduled_start = datetime.fromisoformat(data["scheduled_start"])
            except (ValueError, TypeError):
                tp = self.time_parser.parse(str(data["scheduled_start"]))
                if tp and tp.resolved_start:
                    scheduled_start = tp.resolved_start

        task_data = TaskCreate(
            title=title,
            scheduled_start=scheduled_start,
            duration_minutes=data.get("duration_minutes", 60),
            domain_id=data.get("domain_id"),
            priority=data.get("priority", "medium"),
            is_flexible=scheduled_start is None,
        )

        task = self.task_service.create_task(task_data)

        if scheduled_start:
            try:
                remind_before = int(data.get("remind_before_minutes", 15))
                trigger_at = scheduled_start - timedelta(minutes=remind_before)
                reminder = Reminder(
                    task_id=task.id,
                    reminder_type="lead_time",
                    trigger_at=trigger_at,
                )
                self.db.add(reminder)
                self.db.commit()

                # Schedule Telegram notification via notification service
                user_settings = SettingsService(self.db).get_settings()
                telegram_chat_id = user_settings.telegram_chat_id
                if telegram_chat_id:
                    # Convert local trigger_at to UTC before dispatching
                    trigger_at_utc = trigger_at - timedelta(minutes=getattr(self, '_utc_offset_minutes', 0))
                    # Use LLM-written message if provided, otherwise fall back to a default
                    notify_body = data.get("notify_message") or f"Starting at {scheduled_start.strftime('%H:%M')}."
                    await self._notif_client.schedule_notification(
                        notification_id=f"reminder-{task.id}",
                        telegram_chat_id=telegram_chat_id,
                        title=f"⏰ {title}",
                        body=notify_body,
                        trigger_at=trigger_at_utc.isoformat(),
                    )
            except Exception as e:
                logger.warning("Failed to create reminder/notification: %s", e)

        return [SystemEvent(
            type="task_created",
            message=f"Created: {title}",
            data={"task_id": task.id, "title": title},
        )]

    def _action_delete_tasks(self, data: dict) -> list[SystemEvent]:
        task_ids = data.get("task_ids", [])
        events = []
        for tid in task_ids:
            try:
                task = self.db.get(Task, int(tid))
                if task:
                    title = task.title
                    self.db.query(Reminder).filter(Reminder.task_id == task.id).delete()
                    self.db.delete(task)
                    self.db.commit()
                    events.append(SystemEvent(
                        type="task_deleted",
                        message=f"Deleted: {title}",
                        data={"task_id": int(tid), "title": title},
                    ))
            except Exception as e:
                logger.warning("Failed to delete task %s: %s", tid, e)
        return events

    def _action_complete_tasks(self, data: dict) -> list[SystemEvent]:
        task_ids = data.get("task_ids", [])
        events = []
        for tid in task_ids:
            task = self.task_service.complete_task(int(tid))
            if task:
                events.append(SystemEvent(
                    type="task_completed",
                    message=f"Completed: {task.title}",
                    data={"task_id": int(tid), "title": task.title},
                ))
        return events

    def _action_update_task(self, data: dict) -> list[SystemEvent]:
        from app.schemas.task import TaskUpdate

        tid = data.get("task_id")
        if not tid:
            return []

        update_fields = {}
        for key in ("title", "priority", "domain_id", "duration_minutes"):
            if key in data and data[key] is not None:
                update_fields[key] = data[key]
        if "scheduled_start" in data and data["scheduled_start"]:
            try:
                update_fields["scheduled_start"] = datetime.fromisoformat(
                    data["scheduled_start"]
                )
                update_fields["is_flexible"] = False
            except (ValueError, TypeError):
                pass

        if not update_fields:
            return []

        task = self.task_service.update_task(int(tid), TaskUpdate(**update_fields))
        if task:
            return [SystemEvent(
                type="task_updated",
                message=f"Updated: {task.title}",
                data={"task_id": int(tid), "title": task.title},
            )]
        return []

    # ── Helpers ────────────────────────────────────────────────────────

    def _format_tasks(self, tasks: list[Task]) -> str:
        lines = []
        for t in tasks:
            time_str = (
                t.scheduled_start.strftime("%a %b %d, %I:%M %p")
                if t.scheduled_start
                else "unscheduled"
            )
            lines.append(
                f"- [id={t.id}] {t.title} | {time_str} | "
                f"priority={t.priority} | domain_id={t.domain_id}"
            )
        return "\n".join(lines)

    def _build_live_context(self, events: list[SystemEvent]) -> LiveContext | None:
        if not events:
            return None
        for event in events:
            if event.type == "conflict_detected":
                return LiveContext(type="conflict", data=event.data)
            if event.type == "task_created":
                return LiveContext(type="task_preview", data=event.data)
        return None
