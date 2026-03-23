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
Times should be in HH:MM 24-hour format.

IMPORTANT RULES:
- Respond ONLY with valid JSON matching one of the schemas below. No markdown, no explanation.
- Use the employee_id from the context provided, never guess.
- If the request is ambiguous or you cannot determine the intent, respond with:
  {{"intent_type": "UNCLEAR", "message": "description of what is unclear"}}
- If the request doesn't match any allowed type, respond with:
  {{"intent_type": "UNSUPPORTED", "message": "description"}}
- For time ranges, round to the nearest hour boundary.
- For availability changes, infer the rule_type from context (e.g. "I can't work" = UNAVAILABLE, "I'd like to work" = PREFERRED, "I'm available" = AVAILABLE).

SCHEMAS:
{schemas_text}"""


def build_user_prompt(input_text: str, context: dict) -> str:
    """Build user prompt with input text and org context."""

    context_str = json.dumps(context, indent=2, default=str)

    return f"""User request: "{input_text}"

Context:
{context_str}

Convert this request into the appropriate JSON intent. Respond with JSON only."""