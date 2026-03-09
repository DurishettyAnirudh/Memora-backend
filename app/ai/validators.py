"""Validators — JSON schema validation and repair for LLM output."""

import json
import re
from typing import Any


def parse_llm_json(raw: str) -> dict | list | None:
    """Parse JSON from LLM output, handling common formatting issues."""
    if not raw:
        return None

    cleaned = raw.strip()

    # Strip reasoning model <think>...</think> blocks
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned).strip()

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fix trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from surrounding text
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Fix single quotes → double quotes
    fixed = cleaned.replace("'", '"')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def validate_semantic_understanding(data: dict) -> dict:
    """Validate and fill defaults for Stage 1 output."""
    defaults = {
        "user_intent_summary": "",
        "entities": [],
        "time_signals": [],
        "urgency": "medium",
        "requires_action": True,
        "action_count": 1,
        "emotional_context": None,
        "ambiguities": [],
    }

    result = {**defaults}
    for key in defaults:
        if key in data and data[key] is not None:
            result[key] = data[key]

    # Ensure list types
    for list_key in ["entities", "time_signals", "ambiguities"]:
        if not isinstance(result[list_key], list):
            result[list_key] = []

    # Validate urgency
    if result["urgency"] not in ("high", "medium", "low"):
        result["urgency"] = "medium"

    return result


def validate_structured_intent(data: dict) -> dict:
    """Validate and fill defaults for Stage 2 output."""
    valid_intents = {"create", "read", "update", "delete", "plan", "reflect"}

    result = {
        "intent_type": data.get("intent_type", "create"),
        "tasks": data.get("tasks", []),
        "target_task_ref": data.get("target_task_ref"),
        "query_type": data.get("query_type"),
    }

    if result["intent_type"] not in valid_intents:
        result["intent_type"] = "create"

    # Validate each task
    validated_tasks = []
    for task in result["tasks"]:
        if not isinstance(task, dict):
            continue

        validated = {
            "title": task.get("title", ""),
            "time_expression": task.get("time_expression", ""),
            "duration_minutes": _safe_int(task.get("duration_minutes"), 60),
            "domain_name": task.get("domain_name", "Errands"),
            "priority": task.get("priority", "medium"),
            "reminder": bool(task.get("reminder", True)),
            "project_name": task.get("project_name"),
        }

        # Validate priority
        if validated["priority"] not in ("high", "medium", "low"):
            validated["priority"] = "medium"

        # Ensure title is not empty
        if validated["title"]:
            validated_tasks.append(validated)

    result["tasks"] = validated_tasks
    return result


def _safe_int(value: Any, default: int) -> int:
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
