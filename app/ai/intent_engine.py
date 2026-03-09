"""Intent Inference Engine — 3-stage NLU pipeline."""

import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.ai.client import chat_completion, chat_completion_with_memori
from app.ai.prompts.semantic_understanding import SEMANTIC_UNDERSTANDING_PROMPT
from app.ai.prompts.structured_extraction import STRUCTURED_EXTRACTION_PROMPT
from app.ai.prompts.clarification import CLARIFICATION_PROMPT
from app.ai.time_parser import TimeParser, TimeParse
from app.ai.entity_resolver import EntityResolver
from app.ai.validators import (
    parse_llm_json,
    validate_semantic_understanding,
    validate_structured_intent,
)
from app.config import settings
from app.models.domain import Domain


@dataclass
class TaskIntent:
    title: str
    time_expression: str
    time_parsed: TimeParse | None = None
    duration_minutes: int = 60
    domain_id: int | None = None
    domain_name: str = "Errands"
    priority: str = "medium"
    reminder: bool = True
    project_name: str | None = None


@dataclass
class IntentResult:
    intent_type: str  # create, read, update, delete, plan, reflect
    tasks: list[TaskIntent] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = 0.0
    raw_understanding: str = ""
    target_task_ref: str | None = None
    query_type: str | None = None


class IntentEngine:
    """Three-stage NLU pipeline: Understand → Extract → Validate."""

    def __init__(self, db: Session):
        self.db = db
        self.time_parser = TimeParser()
        self.entity_resolver = EntityResolver()

    def process(
        self,
        user_message: str,
        session_id: str | None = None,
        recent_messages: list[str] | None = None,
    ) -> IntentResult:
        """Run the full 3-stage pipeline."""
        now = datetime.now(timezone.utc)

        # Load context
        domains = self.db.query(Domain).filter(Domain.is_archived == False).all()  # noqa: E712
        domain_names = [d.name for d in domains]
        domain_map = {d.name.lower(): d.id for d in domains}

        # Stage 1: Semantic Understanding
        understanding = self._stage1_semantic_understanding(
            user_message, now, domain_names, recent_messages, session_id
        )

        # Stage 2: Structured Extraction
        structured = self._stage2_structured_extraction(
            understanding, now, domain_names
        )

        # Stage 3: Validation & Repair
        result = self._stage3_validate_and_repair(
            structured, understanding, domain_map
        )

        # If LLM pipeline produced nothing useful, try regex fallback
        if result.needs_clarification and result.intent_type == "create":
            fallback = self._regex_fallback(user_message, domain_map)
            if fallback and fallback.tasks:
                logger.info("LLM pipeline empty — using regex fallback")
                return fallback

        return result

    def _stage1_semantic_understanding(
        self,
        user_message: str,
        now: datetime,
        domains: list[str],
        recent_messages: list[str] | None,
        session_id: str | None,
    ) -> dict:
        """LLM Call 1: Read the message in context, produce rich semantic parse."""
        prompt = SEMANTIC_UNDERSTANDING_PROMPT.format(
            current_datetime=now.strftime("%Y-%m-%d %H:%M %A"),
            work_start=9,
            work_end=17,
            domains=", ".join(domains),
            recent_messages="\n".join(recent_messages or []),
            user_message=user_message,
        )

        try:
            raw = chat_completion_with_memori(
                user_message=user_message,
                system_prompt=prompt,
                session_id=session_id,
                temperature=0.3,
                max_tokens=4096,
            )
            logger.info("Stage 1 raw LLM response: %s", raw[:500] if raw else "(empty)")
        except Exception as e:
            logger.error("Stage 1 LLM call failed: %s", e)
            # LLM call failed — return minimal understanding
            return {
                "user_intent_summary": user_message,
                "entities": [],
                "time_signals": [],
                "urgency": "medium",
                "requires_action": True,
                "action_count": 1,
                "ambiguities": [],
            }

        parsed = parse_llm_json(raw)
        logger.info("Stage 1 parsed JSON: %s", parsed)
        if parsed and isinstance(parsed, dict):
            return validate_semantic_understanding(parsed)

        logger.warning("Stage 1 JSON parse failed, returning fallback. Raw: %s", raw[:300] if raw else "(empty)")
        return {
            "user_intent_summary": user_message,
            "entities": [],
            "time_signals": [],
            "urgency": "medium",
            "requires_action": True,
            "action_count": 1,
            "ambiguities": [],
            "_raw": raw,
        }

    def _stage2_structured_extraction(
        self,
        understanding: dict,
        now: datetime,
        domains: list[str],
    ) -> dict:
        """LLM Call 2: Convert semantic understanding to structured intent."""
        import json

        prompt = STRUCTURED_EXTRACTION_PROMPT.format(
            current_datetime=now.strftime("%Y-%m-%d %H:%M %A"),
            work_start=9,
            work_end=17,
            default_duration=60,
            domains=", ".join(domains),
            understanding=json.dumps(understanding, default=str),
        )

        try:
            raw = chat_completion(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Extract the structured intent."},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            logger.info("Stage 2 raw LLM response: %s", raw[:500] if raw else "(empty)")
        except Exception as e:
            logger.error("Stage 2 LLM call failed: %s", e)
            return {"intent_type": "create", "tasks": []}

        parsed = parse_llm_json(raw)
        logger.info("Stage 2 parsed JSON: %s", parsed)
        if parsed and isinstance(parsed, dict):
            return validate_structured_intent(parsed)

        logger.warning("Stage 2 JSON parse failed, retrying. Raw: %s", raw[:300] if raw else "(empty)")
        # Retry with stricter instructions
        try:
            raw2 = chat_completion(
                messages=[
                    {"role": "system", "content": prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No explanation."},
                    {"role": "user", "content": "Extract the structured intent as JSON only."},
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            parsed2 = parse_llm_json(raw2)
            if parsed2 and isinstance(parsed2, dict):
                return validate_structured_intent(parsed2)
        except Exception:
            pass

        return {"intent_type": "create", "tasks": []}

    def _stage3_validate_and_repair(
        self,
        structured: dict,
        understanding: dict,
        domain_map: dict[str, int],
    ) -> IntentResult:
        """No LLM call — deterministic validation and repair."""
        intent_type = structured.get("intent_type", "create")
        tasks_data = structured.get("tasks", [])

        # Build TaskIntent objects
        task_intents = []
        for task_data in tasks_data:
            # Parse time
            time_expr = task_data.get("time_expression", "")
            time_parsed = self.time_parser.parse(time_expr) if time_expr else None

            # Resolve domain
            domain_name = task_data.get("domain_name", "Errands")
            domain_id = domain_map.get(domain_name.lower())
            if domain_id is None:
                # Fallback to Errands
                domain_id = domain_map.get("errands")

            task_intents.append(TaskIntent(
                title=task_data.get("title", ""),
                time_expression=time_expr,
                time_parsed=time_parsed,
                duration_minutes=task_data.get("duration_minutes", 60),
                domain_id=domain_id,
                domain_name=domain_name,
                priority=task_data.get("priority", "medium"),
                reminder=task_data.get("reminder", True),
                project_name=task_data.get("project_name"),
            ))

        # Check if clarification is needed
        needs_clarification = False
        clarification_q = None

        if intent_type == "create" and not task_intents:
            needs_clarification = True
            clarification_q = "I'm not sure what you'd like me to schedule. Could you tell me more?"

        elif intent_type in ("update", "delete") and not structured.get("target_task_ref"):
            needs_clarification = True
            clarification_q = "Which task are you referring to?"

        # Check ambiguities from Stage 1
        ambiguities = understanding.get("ambiguities", [])
        if ambiguities and not needs_clarification:
            # Only ask if ambiguity is critical
            critical = [a for a in ambiguities if "time" in a.lower() or "which" in a.lower()]
            if critical:
                needs_clarification = True
                try:
                    clarification_q = self._generate_clarification(understanding, critical)
                except Exception:
                    clarification_q = critical[0]

        # Calculate confidence
        confidence = 0.8
        if needs_clarification:
            confidence = 0.3
        elif any(t.time_parsed and t.time_parsed.is_flexible for t in task_intents):
            confidence = 0.6

        return IntentResult(
            intent_type=intent_type,
            tasks=task_intents,
            needs_clarification=needs_clarification,
            clarification_question=clarification_q,
            confidence=confidence,
            raw_understanding=understanding.get("user_intent_summary", ""),
            target_task_ref=structured.get("target_task_ref"),
            query_type=structured.get("query_type"),
        )

    def _generate_clarification(self, understanding: dict, ambiguities: list[str]) -> str:
        """Generate a natural clarification question."""
        import json

        prompt = CLARIFICATION_PROMPT.format(
            known_context=json.dumps(understanding, default=str),
            ambiguities=", ".join(ambiguities),
        )

        return chat_completion(
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )

    def _regex_fallback(
        self, user_message: str, domain_map: dict[str, int]
    ) -> IntentResult | None:
        """Simple regex-based intent parser for when LLM is unavailable."""
        msg = user_message.strip()
        if not msg or len(msg) < 3:
            return None

        # Detect read/query intents
        read_patterns = [
            r"^(what|show|list|tell|display|how many|when)\b",
            r"^(do i have|what\'?s)\b",
        ]
        for p in read_patterns:
            if re.search(p, msg, re.IGNORECASE):
                return IntentResult(
                    intent_type="read",
                    tasks=[],
                    needs_clarification=False,
                    confidence=0.5,
                    raw_understanding=msg,
                    query_type="schedule",
                )

        # Detect delete intents
        if re.search(r"^(delete|remove|cancel)\b", msg, re.IGNORECASE):
            return IntentResult(
                intent_type="delete",
                tasks=[],
                needs_clarification=True,
                clarification_question="Which task would you like me to delete?",
                confidence=0.4,
                raw_understanding=msg,
            )

        # Default: treat as a task creation
        # Try to extract time expression
        time_expr = ""
        time_patterns = [
            r"(today|tonight|this morning|this afternoon|this evening)",
            r"(tomorrow|tmrw|tmr)\s*(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?",
            r"(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month))",
            r"(on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
            r"(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        ]
        for p in time_patterns:
            m = re.search(p, msg, re.IGNORECASE)
            if m:
                time_expr = m.group(0).strip()
                break

        # Extract title: remove time expression from message
        title = msg
        if time_expr:
            # Remove common prefixes
            title = re.sub(
                r"^(i\s+want\s+to|i\s+need\s+to|i\s+have\s+to|"
                r"i\'?d\s+like\s+to|can\s+you|please|remind\s+me\s+to|"
                r"schedule|add|create|book|plan)\s+",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()
            title = title.replace(time_expr, "").strip()
            # Clean up leftover prepositions
            title = re.sub(r"\s+(at|on|by|for|in)\s*$", "", title).strip()
        else:
            title = re.sub(
                r"^(i\s+want\s+to|i\s+need\s+to|i\s+have\s+to|"
                r"i\'?d\s+like\s+to|can\s+you|please|remind\s+me\s+to|"
                r"schedule|add|create|book|plan)\s+",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()

        if not title:
            title = msg

        # Guess domain from keywords
        domain_name = "Errands"
        domain_keywords = {
            "work": ["meeting", "standup", "review", "deploy", "code", "office", "client", "presentation"],
            "personal": ["temple", "church", "mosque", "family", "friend", "dinner", "lunch", "movie", "party", "call mom", "call dad"],
            "health": ["gym", "run", "yoga", "doctor", "dentist", "medication", "workout", "exercise", "walk"],
            "finance": ["pay", "bill", "tax", "invoice", "budget", "bank"],
            "learning": ["study", "read", "course", "class", "lecture", "tutorial", "learn"],
        }
        msg_lower = msg.lower()
        for dom, keywords in domain_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                domain_name = dom.capitalize()
                break

        domain_id = domain_map.get(domain_name.lower()) or domain_map.get("errands")

        # Parse time
        time_parsed = self.time_parser.parse(time_expr) if time_expr else None

        task = TaskIntent(
            title=title.capitalize() if title[0].islower() else title,
            time_expression=time_expr,
            time_parsed=time_parsed,
            duration_minutes=60,
            domain_id=domain_id,
            domain_name=domain_name,
            priority="medium",
            reminder=True,
        )

        return IntentResult(
            intent_type="create",
            tasks=[task],
            needs_clarification=False,
            confidence=0.5,
            raw_understanding=msg,
        )
