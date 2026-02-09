"""
AI service - main orchestration layer.
Takes user input, builds context, calls LLM, creates output + proposal records.
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs, AIOutputStatus
from app.db.models.ai_proposals import AIProposals, ProposalType, ProposalStatus
from app.db.models.users import Users
from app.api.deps import is_manager_or_admin

from .llm_provider import get_llm_provider, LLMResponse
from .context_loader import (
    load_employee_context,
    load_store_context,
    load_coverage_context,
    load_store_employees_context,
)
from .intent_schemas import INTENT_SCHEMAS, DAY_MAP
from .prompts import build_system_prompt, build_user_prompt


logger = logging.getLogger(__name__)

INTENT_TO_PROPOSAL_TYPE = {
    "AVAILABILITY": ProposalType.AVAILABILITY,
    "COVERAGE": ProposalType.COVERAGE,
    "ROLE_REQUIREMENT": ProposalType.ROLE_REQUIREMENT,
}


def process_ai_input(db: Session, ai_input: AIInputs, current_user: Users) -> AIOutputs:
    """
    Main entry point. Processes an AI input and creates output + proposal.

    Flow:
    1. Determine user role (employee vs manager/admin)
    2. Load relevant context from DB
    3. Build prompt with context + schemas
    4. Call LLM
    5. Validate and create AIOutput
    6. Create AIProposal if output is valid
    7. Mark input as processed
    """
    # 1. Determine role context
    is_mgr_or_admin = is_manager_or_admin(db, current_user)
    employee_ctx = load_employee_context(db, current_user.id)

    if not employee_ctx:
        return _create_error_output(db, ai_input, "No employee record found for user")

    store_id = employee_ctx["store_id"]

    # 2. Build context based on role
    context = {"employee": employee_ctx}

    if is_mgr_or_admin:
        store_ctx = load_store_context(db, store_id)
        if store_ctx:
            context["store"] = store_ctx
        context["coverage_requirements"] = load_coverage_context(db, store_id)
        context["store_employees"] = load_store_employees_context(db, store_id)

    # 3. Build prompts
    allowed_types = _get_allowed_types(is_mgr_or_admin)
    system_prompt = build_system_prompt(allowed_types, is_mgr_or_admin)
    user_prompt = build_user_prompt(ai_input.input_text, context)

    # 4. Call LLM
    provider = get_llm_provider()
    llm_response = provider.generate_json(system_prompt, user_prompt)

    if not llm_response.success or not llm_response.parsed_json:
        return _create_error_output(
            db, ai_input,
            f"LLM processing failed: {llm_response.error}",
            model_used=llm_response.model_used,
        )

    result = llm_response.parsed_json

    # 5. Validate intent type
    intent_type = result.get("intent_type")
    if not intent_type or intent_type not in INTENT_TO_PROPOSAL_TYPE:
        # TODO: Implement NEEDS_CLARIFICATION flow instead of error
        if intent_type == "LABOUR_BUDGET":
            return _create_error_output(
                db, ai_input,
                "Labour budget changes are not yet supported",
                model_used=llm_response.model_used,
            )
        return _create_error_output(
            db, ai_input,
            f"Unrecognised intent type: {intent_type}",
            model_used=llm_response.model_used,
        )

    # Permission check - employees can only request availability changes
    if not is_mgr_or_admin and intent_type != "AVAILABILITY":
        return _create_error_output(
            db, ai_input,
            "Employees can only request availability changes",
            model_used=llm_response.model_used,
        )

    # 6. Create output
    summary = result.get("summary", "AI-generated constraint change proposal")

    # For availability changes, set affects_user_id
    affects_user_id = None
    if intent_type == "AVAILABILITY":
        affects_user_id = current_user.id
        # If manager is changing someone else's availability, use the target employee's user
        target_emp_id = result.get("employee_id")
        if target_emp_id and is_mgr_or_admin:
            from app.db.models.employees import Employees
            target_emp = db.query(Employees).filter(Employees.id == target_emp_id).first()
            if target_emp:
                affects_user_id = target_emp.user_id

    ai_output = AIOutputs(
        input_id=ai_input.id,
        result_json=result,
        summary=summary,
        status=AIOutputStatus.COMPLETE,
        model_used=llm_response.model_used,
        affects_user_id=affects_user_id,
    )
    db.add(ai_output)
    db.flush()  # get ai_output.id without committing

    # 7. Create proposal
    proposal_type = INTENT_TO_PROPOSAL_TYPE[intent_type]

    proposal = AIProposals(
        ai_output_id=ai_output.id,
        type=proposal_type,
        store_id=result.get("store_id", store_id),
        department_id=result.get("department_id"),
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)

    # 8. Mark input processed
    ai_input.processed = True

    db.commit()
    db.refresh(ai_output)
    return ai_output


def _get_allowed_types(is_mgr_or_admin: bool) -> List[str]:
    if is_mgr_or_admin:
        return ["AVAILABILITY", "COVERAGE", "ROLE_REQUIREMENT"]
    return ["AVAILABILITY"]


def _create_error_output(
    db: Session,
    ai_input: AIInputs,
    error_msg: str,
    model_used: str = "none",
) -> AIOutputs:
    """Create an INVALID output for failed processing."""
    ai_output = AIOutputs(
        input_id=ai_input.id,
        result_json={"error": error_msg},
        summary=error_msg,
        status=AIOutputStatus.INVALID,
        model_used=model_used,
    )
    db.add(ai_output)
    ai_input.processed = True
    db.commit()
    db.refresh(ai_output)
    return ai_output