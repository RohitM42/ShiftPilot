"""
Proposal approval handlers.
When a proposal is approved, apply the actual changes to the relevant constraint tables.
"""

import logging
from datetime import time
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.ai_outputs import AIOutputs
from app.db.models.ai_proposals import AIProposals, ProposalType
from app.db.models.availability_rules import AvailabilityRules, AvailabilityRuleType
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.role_requirements import RoleRequirements


logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    pass


def apply_proposal(db: Session, proposal: AIProposals, approved_by_user_id: int) -> None:
    """
    Apply an approved proposal's changes to the relevant constraint table.
    Called after proposal status is set to APPROVED.
    """
    output = db.query(AIOutputs).filter(AIOutputs.id == proposal.ai_output_id).first()
    if not output:
        raise ApprovalError("AI output not found for proposal")

    result = output.result_json
    intent_type = result.get("intent_type")

    handlers = {
        "AVAILABILITY": _apply_availability_changes,
        "COVERAGE": _apply_coverage_changes,
        "ROLE_REQUIREMENT": _apply_role_requirement_changes,
    }

    handler = handlers.get(intent_type)
    if not handler:
        raise ApprovalError(f"No handler for intent type: {intent_type}")

    handler(db, result, approved_by_user_id)


def _parse_time(t: Optional[str]) -> Optional[time]:
    """Parse HH:MM string to time object."""
    if not t:
        return None
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


def _apply_availability_changes(db: Session, result: dict, approved_by: int) -> None:
    """Apply availability rule changes."""
    employee_id = result["employee_id"]
    changes = result.get("changes", [])

    for change in changes:
        action = change["action"]
        day = change["day_of_week"]
        start = _parse_time(change.get("start_time"))
        end = _parse_time(change.get("end_time"))
        rule_type = AvailabilityRuleType(change["rule_type"])

        if action == "ADD":
            rule = AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=start,
                end_time_local=end,
                rule_type=rule_type,
                active=True,
            )
            db.add(rule)

        elif action == "REMOVE":
            # Find matching active rules and deactivate
            query = db.query(AvailabilityRules).filter(
                AvailabilityRules.employee_id == employee_id,
                AvailabilityRules.day_of_week == day,
                AvailabilityRules.active == True,
            )
            if start and end:
                query = query.filter(
                    AvailabilityRules.start_time_local == start,
                    AvailabilityRules.end_time_local == end,
                )
            rules = query.all()
            for r in rules:
                r.active = False

        elif action == "UPDATE":
            # Deactivate existing rules for this day/time and add new one
            query = db.query(AvailabilityRules).filter(
                AvailabilityRules.employee_id == employee_id,
                AvailabilityRules.day_of_week == day,
                AvailabilityRules.active == True,
            )
            for r in query.all():
                r.active = False

            rule = AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=start,
                end_time_local=end,
                rule_type=rule_type,
                active=True,
            )
            db.add(rule)


def _apply_coverage_changes(db: Session, result: dict, approved_by: int) -> None:
    """Apply coverage requirement changes."""
    store_id = result["store_id"]
    department_id = result["department_id"]
    changes = result.get("changes", [])

    for change in changes:
        action = change["action"]

        if action == "ADD":
            req = CoverageRequirements(
                store_id=store_id,
                department_id=department_id,
                day_of_week=change["day_of_week"],
                start_time_local=_parse_time(change["start_time"]),
                end_time_local=_parse_time(change["end_time"]),
                min_staff=change["min_staff"],
                max_staff=change.get("max_staff"),
                active=True,
                last_modified_by_user_id=approved_by,
            )
            db.add(req)

        elif action == "REMOVE":
            cov_id = change.get("coverage_id")
            if cov_id:
                req = db.query(CoverageRequirements).filter(
                    CoverageRequirements.id == cov_id,
                    CoverageRequirements.store_id == store_id,
                ).first()
                if req:
                    req.active = False
                    req.last_modified_by_user_id = approved_by

        elif action == "UPDATE":
            cov_id = change.get("coverage_id")
            if cov_id:
                req = db.query(CoverageRequirements).filter(
                    CoverageRequirements.id == cov_id,
                    CoverageRequirements.store_id == store_id,
                ).first()
                if req:
                    if "min_staff" in change:
                        req.min_staff = change["min_staff"]
                    if "max_staff" in change:
                        req.max_staff = change["max_staff"]
                    if "start_time" in change:
                        req.start_time_local = _parse_time(change["start_time"])
                    if "end_time" in change:
                        req.end_time_local = _parse_time(change["end_time"])
                    req.last_modified_by_user_id = approved_by


def _apply_role_requirement_changes(db: Session, result: dict, approved_by: int) -> None:
    """Apply role requirement changes."""
    store_id = result["store_id"]
    department_id = result.get("department_id")
    changes = result.get("changes", [])

    for change in changes:
        action = change["action"]

        if action == "ADD":
            req = RoleRequirements(
                store_id=store_id,
                department_id=department_id,
                day_of_week=change.get("day_of_week"),
                start_time_local=_parse_time(change["start_time"]),
                end_time_local=_parse_time(change["end_time"]),
                requires_keyholder=change.get("requires_keyholder", False),
                requires_manager=change.get("requires_manager", False),
                min_manager_count=change.get("min_manager_count", 0),
                active=True,
            )
            db.add(req)

        elif action == "REMOVE":
            req_id = change.get("role_requirement_id")
            if req_id:
                req = db.query(RoleRequirements).filter(
                    RoleRequirements.id == req_id,
                    RoleRequirements.store_id == store_id,
                ).first()
                if req:
                    req.active = False

        elif action == "UPDATE":
            req_id = change.get("role_requirement_id")
            if req_id:
                req = db.query(RoleRequirements).filter(
                    RoleRequirements.id == req_id,
                    RoleRequirements.store_id == store_id,
                ).first()
                if req:
                    for field in ["requires_keyholder", "requires_manager", "min_manager_count"]:
                        if field in change:
                            setattr(req, field, change[field])
                    if "start_time" in change:
                        req.start_time_local = _parse_time(change["start_time"])
                    if "end_time" in change:
                        req.end_time_local = _parse_time(change["end_time"])