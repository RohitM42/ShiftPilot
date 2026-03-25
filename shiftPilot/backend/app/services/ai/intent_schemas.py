"""
JSON intent schemas for AI-generated proposals.
Defines the structure the LLM must output for each proposal type.
These schemas are included in the system prompt so the LLM knows what to return.
"""

# Day mapping included in prompts for LLM reference
DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

AVAILABILITY_INTENT_SCHEMA = {
    "description": "Change to an employee's weekly availability rules",
    "schema": {
        "intent_type": "AVAILABILITY",
        "employee_id": "int - the employee this affects",
        "changes": [
            {
                "action": "ADD | REMOVE | UPDATE",
                "day_of_week": "int 0-6 (0=Monday, 6=Sunday)",
                "start_time": "HH:MM or null (null = all day)",
                "end_time": "HH:MM or null (null = all day)",
                "rule_type": "AVAILABLE | UNAVAILABLE | PREFERRED",
            }
        ],
        "summary": "Human-readable summary of the change",
    },
    "examples": [
        {
            "input": "I can't work Tuesdays anymore",
            "output": {
                "intent_type": "AVAILABILITY",
                "employee_id": 5,
                "changes": [
                    {"action": "ADD", "day_of_week": 1, "start_time": None, "end_time": None, "rule_type": "UNAVAILABLE"}
                ],
                "summary": "Marking Tuesdays as unavailable (all day)",
            },
        },
        {
            "input": "I'd prefer to work mornings on weekdays",
            "output": {
                "intent_type": "AVAILABILITY",
                "employee_id": 5,
                "changes": [
                    {"action": "ADD", "day_of_week": d, "start_time": "06:00", "end_time": "12:00", "rule_type": "PREFERRED"}
                    for d in range(5)
                ],
                "summary": "Setting preferred hours as 06:00-12:00 Monday to Friday",
            },
        },
    ],
}

COVERAGE_INTENT_SCHEMA = {
    "description": "Change to store/department coverage requirements",
    "schema": {
        "intent_type": "COVERAGE",
        "store_id": "int",
        "department_id": "int",
        "changes": [
            {
                "action": "ADD | REMOVE | UPDATE",
                "day_of_week": "int 0-6",
                "start_time": "HH:MM",
                "end_time": "HH:MM",
                "min_staff": "int (always absolute, never a delta)",
                "coverage_id": "int or null (required for UPDATE/REMOVE, null for ADD)",
            }
        ],
        "summary": "Human-readable summary of the change",
    },
    "examples": [
        {
            "input": "We need 3 people on the shop floor on Saturdays from 10am to 4pm",
            "output": {
                "intent_type": "COVERAGE",
                "store_id": 1,
                "department_id": 2,
                "changes": [
                    {"action": "ADD", "day_of_week": 5, "start_time": "10:00", "end_time": "16:00", "min_staff": 3, "coverage_id": None}
                ],
                "summary": "Adding coverage requirement: 3 staff minimum for Shop Floor on Saturdays 10:00-16:00",
            },
        },
        {
            "input": "We need one extra person in the bakery on Sundays from 9am to 5pm [context shows existing rule id=7: Bakery, Sunday 09:00-17:00, min_staff=2 — so 2+1=3]",
            "output": {
                "intent_type": "COVERAGE",
                "store_id": 1,
                "department_id": 3,
                "changes": [
                    {"action": "UPDATE", "day_of_week": 6, "start_time": "09:00", "end_time": "17:00", "min_staff": 3, "coverage_id": 7}
                ],
                "summary": "Updating Bakery Sunday 09:00-17:00 coverage from 2 to 3 minimum staff",
            },
        },
        {
            "input": "Remove the Saturday afternoon coverage rule for the bakery [context shows existing rule id=9: Bakery, Saturday 13:00-18:00, min_staff=1]",
            "output": {
                "intent_type": "COVERAGE",
                "store_id": 1,
                "department_id": 3,
                "changes": [
                    {"action": "REMOVE", "day_of_week": 5, "start_time": "13:00", "end_time": "18:00", "min_staff": 1, "coverage_id": 9}
                ],
                "summary": "Removing Bakery Saturday 13:00-18:00 coverage requirement",
            },
        },
    ],
}

ROLE_REQUIREMENT_INTENT_SCHEMA = {
    "description": "Change to role requirements (keyholder/manager presence)",
    "schema": {
        "intent_type": "ROLE_REQUIREMENT",
        "store_id": "int",
        "department_id": "int or null (null = whole store)",
        "changes": [
            {
                "action": "ADD | REMOVE | UPDATE",
                "day_of_week": "int 0-6 or null (null = every day)",
                "start_time": "HH:MM",
                "end_time": "HH:MM",
                "requires_keyholder": "bool",
                "requires_manager": "bool",
                "min_manager_count": "int",
                "role_requirement_id": "int or null (required for UPDATE/REMOVE, null for ADD)",
            }
        ],
        "summary": "Human-readable summary of the change",
    },
    "examples": [
        {
            "input": "A manager must be present every day from 9am to 6pm",
            "output": {
                "intent_type": "ROLE_REQUIREMENT",
                "store_id": 1,
                "department_id": None,
                "changes": [
                    {"action": "ADD", "day_of_week": None, "start_time": "09:00", "end_time": "18:00", "requires_keyholder": False, "requires_manager": True, "min_manager_count": 1, "role_requirement_id": None}
                ],
                "summary": "Requiring a manager to be present every day 09:00-18:00",
            },
        },
        {
            "input": "We no longer need a keyholder on Sunday mornings [context shows existing rule id=4: Sunday 08:00-12:00, requires_keyholder=true]",
            "output": {
                "intent_type": "ROLE_REQUIREMENT",
                "store_id": 1,
                "department_id": None,
                "changes": [
                    {"action": "REMOVE", "day_of_week": 6, "start_time": "08:00", "end_time": "12:00", "requires_keyholder": True, "requires_manager": False, "min_manager_count": 0, "role_requirement_id": 4}
                ],
                "summary": "Removing keyholder requirement for Sunday mornings 08:00-12:00",
            },
        },
    ],
}

# Mapping from intent type to schema for prompt building
INTENT_SCHEMAS = {
    "AVAILABILITY": AVAILABILITY_INTENT_SCHEMA,
    "COVERAGE": COVERAGE_INTENT_SCHEMA,
    "ROLE_REQUIREMENT": ROLE_REQUIREMENT_INTENT_SCHEMA,
}