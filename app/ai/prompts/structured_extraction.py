"""Stage 2 prompt — Structured Extraction."""

STRUCTURED_EXTRACTION_PROMPT = """You are Memora's structured extraction module. Convert the semantic understanding into actionable structured data.

## Context
- Current date/time: {current_datetime}
- User's work hours: {work_start}:00 - {work_end}:00
- Default task duration: {default_duration} minutes
- Available domains: {domains}

## Semantic Understanding (from Stage 1)
{understanding}

## Rules
1. For CREATE intents: extract one task object per distinct action
2. For UPDATE/DELETE: identify which existing task is being referenced
3. For READ queries: identify what information is being asked for
4. Map each task to the most appropriate domain from the available list
5. Prefer explicit times over defaults; mark vague times in time_expression
6. Set priority based on urgency signals (deadline closeness, explicit mentions, emotional urgency)
7. If the user mentions a project, include project_name

## Output Format (JSON)
```json
{{
  "intent_type": "create|read|update|delete|plan|reflect",
  "tasks": [
    {{
      "title": "Concise task title",
      "time_expression": "the original time reference (e.g., 'tomorrow at 2pm', 'next week')",
      "duration_minutes": 60,
      "domain_name": "Work|Personal|Health|Projects|Finance|Learning|Errands",
      "priority": "high|medium|low",
      "reminder": true,
      "project_name": null
    }}
  ],
  "target_task_ref": "description of which task to modify (for update/delete)",
  "query_type": "schedule|availability|summary|search (for read intents)"
}}
```

Respond with ONLY the JSON object, no other text."""
