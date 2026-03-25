"""
Prompt construction for AI service.
Builds system and user prompts with context and schema definitions.
"""

import json
from .intent_schemas import INTENT_SCHEMAS, DAY_MAP


def build_system_prompt(allowed_types: list[str], is_manager: bool) -> str:
    """Build system prompt with allowed schemas and role context."""

    role_desc = "a manager or admin" if is_manager else "an employee"
    type_list = ", ".join(allowed_types)

    schemas_text = ""
    for t in allowed_types:
        schema = INTENT_SCHEMAS.get(t)
        if schema:
            schemas_text += f"\n### {t}\n"
            schemas_text += f"Description: {schema['description']}\n"
            schemas_text += f"Schema:\n```json\n{json.dumps(schema['schema'], indent=2)}\n```\n"
            if schema.get("examples"):
                schemas_text += "Examples:\n"
                for ex in schema["examples"]:
                    schemas_text += f"  Input: \"{ex['input']}\"\n"
                    schemas_text += f"  Output: {json.dumps(ex['output'], indent=2)}\n\n"

    return f"""You are an AI assistant for ShiftPilot, a retail workforce scheduling system.
Your job is to interpret natural language requests about scheduling constraints and convert them into structured JSON.

The user is {role_desc}. They can request changes of these types: {type_list}.

Day mapping: {json.dumps(DAY_MAP)}
Times should be in HH:MM 24-hour format. Round to the nearest hour boundary (e.g. "half 9" = 09:00, "quarter past 5" = 17:00).

IMPORTANT RULES:
- Respond ONLY with valid JSON matching one of the schemas below. No markdown, no explanation.
- Use the employee_id from the context provided, never guess.
- If the request is ambiguous, a department is unclear, or you are not confident, respond with:
  {{"intent_type": "UNCLEAR", "message": "description of what is unclear"}}
- If the request doesn't match any allowed type, respond with:
  {{"intent_type": "UNSUPPORTED", "message": "description"}}
- For availability changes, infer the rule_type from context ("I can't work" = UNAVAILABLE, "I'd like to work" = PREFERRED, "I'm available" = AVAILABLE).

STAFFING LEVELS (COVERAGE):
- Always output absolute min_staff values, never deltas.
- If the request uses relative language ("add 1 more", "one extra", "reduce by 2"), look up the existing rule in the coverage_requirements context, then calculate the new absolute value (e.g. existing min_staff=2, "add 1 extra" → output min_staff=3).
- If no matching existing rule is found for a relative request, respond with UNCLEAR.

TARGETING EXISTING RULES (UPDATE / REMOVE):
- For UPDATE and REMOVE actions you must provide the coverage_id or role_requirement_id.
- Find the matching rule in the context by comparing department, day_of_week, and time window.
- If the user's description matches multiple rules (e.g. "the Saturday morning rule"), include one change entry per matching rule.
- If you cannot confidently identify which rule to target, respond with UNCLEAR rather than guessing.

SCHEMAS:
{schemas_text}"""


def build_user_prompt(input_text: str, context: dict) -> str:
    """Build user prompt with input text and org context."""

    context_str = json.dumps(context, indent=2, default=str)

    return f"""User request: "{input_text}"

Context:
{context_str}

Convert this request into the appropriate JSON intent. Respond with JSON only."""