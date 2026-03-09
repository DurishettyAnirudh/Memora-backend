"""Unit tests for LLM JSON validators."""

import pytest

from app.ai.validators import (
    parse_llm_json,
    validate_semantic_understanding,
    validate_structured_intent,
)


class TestParseLlmJson:
    def test_valid_json(self):
        assert parse_llm_json('{"key": "value"}') == {"key": "value"}

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert parse_llm_json(raw) == {"key": "value"}

    def test_json_with_plain_fences(self):
        raw = '```\n{"key": 1}\n```'
        assert parse_llm_json(raw) == {"key": 1}

    def test_trailing_comma_fix(self):
        raw = '{"a": 1, "b": 2,}'
        result = parse_llm_json(raw)
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self):
        raw = '{"items": [1, 2, 3,]}'
        result = parse_llm_json(raw)
        assert result["items"] == [1, 2, 3]

    def test_json_embedded_in_text(self):
        raw = 'Here is the result:\n{"intent": "create"}\nHope that helps!'
        result = parse_llm_json(raw)
        assert result == {"intent": "create"}

    def test_single_quotes_to_double(self):
        raw = "{'key': 'value'}"
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_empty_string(self):
        assert parse_llm_json("") is None

    def test_none_input(self):
        assert parse_llm_json(None) is None

    def test_array_input(self):
        raw = '[{"a": 1}, {"b": 2}]'
        result = parse_llm_json(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_garbage_returns_none(self):
        assert parse_llm_json("not json at all") is None


class TestValidateSemanticUnderstanding:
    def test_fills_defaults(self):
        result = validate_semantic_understanding({})
        assert result["user_intent_summary"] == ""
        assert result["entities"] == []
        assert result["urgency"] == "medium"
        assert result["requires_action"] is True
        assert result["action_count"] == 1

    def test_preserves_valid_data(self):
        data = {
            "user_intent_summary": "Create a task",
            "entities": ["meeting"],
            "urgency": "high",
            "action_count": 2,
        }
        result = validate_semantic_understanding(data)
        assert result["user_intent_summary"] == "Create a task"
        assert result["urgency"] == "high"
        assert result["action_count"] == 2

    def test_corrects_invalid_urgency(self):
        result = validate_semantic_understanding({"urgency": "super"})
        assert result["urgency"] == "medium"

    def test_coerces_non_list_entities(self):
        result = validate_semantic_understanding({"entities": "single"})
        assert result["entities"] == []


class TestValidateStructuredIntent:
    def test_fills_defaults(self):
        result = validate_structured_intent({})
        assert result["intent_type"] == "create"
        assert result["tasks"] == []

    def test_corrects_invalid_intent(self):
        result = validate_structured_intent({"intent_type": "fly_to_moon"})
        assert result["intent_type"] == "create"

    def test_validates_tasks(self):
        data = {
            "intent_type": "create",
            "tasks": [
                {
                    "title": "Meeting",
                    "time_expression": "tomorrow at 2pm",
                    "duration_minutes": 60,
                    "domain_name": "Work",
                    "priority": "high",
                    "reminder": True,
                }
            ],
        }
        result = validate_structured_intent(data)
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Meeting"
        assert result["tasks"][0]["priority"] == "high"

    def test_strips_tasks_without_title(self):
        data = {
            "intent_type": "create",
            "tasks": [
                {"title": "", "time_expression": "now"},
                {"title": "Valid", "time_expression": "now"},
            ],
        }
        result = validate_structured_intent(data)
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Valid"

    def test_corrects_invalid_priority(self):
        data = {
            "intent_type": "create",
            "tasks": [{"title": "X", "priority": "urgent"}],
        }
        result = validate_structured_intent(data)
        assert result["tasks"][0]["priority"] == "medium"

    def test_duration_defaults(self):
        data = {
            "intent_type": "create",
            "tasks": [{"title": "X"}],
        }
        result = validate_structured_intent(data)
        assert result["tasks"][0]["duration_minutes"] == 60

    def test_bad_duration_uses_default(self):
        data = {
            "intent_type": "create",
            "tasks": [{"title": "X", "duration_minutes": "abc"}],
        }
        result = validate_structured_intent(data)
        assert result["tasks"][0]["duration_minutes"] == 60
