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
    Supports both AI proposals (via ai_output.result_json) and manual proposals (via proposal.changes_json).
    """
    if proposal.ai_output_id:
        output = db.query(AIOutputs).filter(AIOutputs.id == proposal.ai_output_id).first()
        if not output:
            raise ApprovalError("AI output not found for proposal")
        result = output.result_json
    elif proposal.changes_json:
        result = proposal.changes_json
    else:
        raise ApprovalError("Proposal has no changes to apply")

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


def _times_overlap(
    new_start: Optional[time],
    new_end: Optional[time],
    ex_start: Optional[time],
    ex_end: Optional[time],
) -> bool:
    """Return True if two time ranges overlap. None means all-day (00:00–24:00)."""
    # Represent all-day as 0 and 1440 minutes for comparison
    ns = 0 if new_start is None else new_start.hour * 60 + new_start.minute
    ne = 1440 if new_end is None else new_end.hour * 60 + new_end.minute
    es = 0 if ex_start is None else ex_start.hour * 60 + ex_start.minute
    ee = 1440 if ex_end is None else ex_end.hour * 60 + ex_end.minute
    return ns < ee and ne > es


def _resolve_conflicts(
    db: Session,
    employee_id: int,
    day: int,
    new_start: Optional[time],
    new_end: Optional[time],
) -> None:
    """
    For every active rule on this day that overlaps the new time range,
    trim, split, or deactivate it so there are no overlapping windows.
    """
    existing = db.query(AvailabilityRules).filter(
        AvailabilityRules.employee_id == employee_id,
        AvailabilityRules.day_of_week == day,
        AvailabilityRules.active == True,
    ).all()

    ns = 0 if new_start is None else new_start.hour * 60 + new_start.minute
    ne = 1440 if new_end is None else new_end.hour * 60 + new_end.minute

    for ex in existing:
        es = 0 if ex.start_time_local is None else ex.start_time_local.hour * 60 + ex.start_time_local.minute
        ee = 1440 if ex.end_time_local is None else ex.end_time_local.hour * 60 + ex.end_time_local.minute

        if not (ns < ee and ne > es):
            continue  # no overlap

        # New rule completely covers existing → deactivate
        if ns <= es and ne >= ee:
            ex.active = False

        # New rule overlaps only the start of existing → trim start forward
        elif ns <= es and ne < ee:
            ex.active = False
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=new_end,
                end_time_local=ex.end_time_local,
                rule_type=ex.rule_type,
                active=True,
            ))

        # New rule overlaps only the end of existing → trim end backward
        elif ns > es and ne >= ee:
            ex.active = False
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=ex.start_time_local,
                end_time_local=new_start,
                rule_type=ex.rule_type,
                active=True,
            ))

        # New rule is inside existing → split into two
        else:
            ex.active = False
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=ex.start_time_local,
                end_time_local=new_start,
                rule_type=ex.rule_type,
                active=True,
            ))
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=new_end,
                end_time_local=ex.end_time_local,
                rule_type=ex.rule_type,
                active=True,
            ))


def _merge_adjacent_same_type(db: Session, employee_id: int, day: int) -> None:
    """
    After inserting a new rule, merge any adjacent active rules of the same type on the same day.
    e.g. 9am-5pm AVAILABLE touching 5pm-midnight AVAILABLE → 9am-midnight AVAILABLE.
    """
    db.flush()  # ensure newly-added rules are visible to the query
    rules = db.query(AvailabilityRules).filter(
        AvailabilityRules.employee_id == employee_id,
        AvailabilityRules.day_of_week == day,
        AvailabilityRules.active == True,
    ).all()

    if len(rules) < 2:
        return

    def _start(r: AvailabilityRules) -> int:
        return 0 if r.start_time_local is None else r.start_time_local.hour * 60 + r.start_time_local.minute

    def _end(r: AvailabilityRules) -> int:
        return 1440 if r.end_time_local is None else r.end_time_local.hour * 60 + r.end_time_local.minute

    sorted_rules = sorted(rules, key=_start)

    i = 0
    while i < len(sorted_rules) - 1:
        cur = sorted_rules[i]
        nxt = sorted_rules[i + 1]
        if cur.rule_type == nxt.rule_type and _end(cur) == _start(nxt):
            cur.end_time_local = nxt.end_time_local
            nxt.active = False
            sorted_rules.pop(i + 1)
        else:
            i += 1


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
            # Resolve any overlapping existing rules before inserting
            _resolve_conflicts(db, employee_id, day, start, end)
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=start,
                end_time_local=end,
                rule_type=rule_type,
                active=True,
            ))
            _merge_adjacent_same_type(db, employee_id, day)

        elif action == "REMOVE":
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
            for r in query.all():
                r.active = False

        elif action == "UPDATE":
            # UPDATE replaces all rules for the day — resolve conflicts then insert
            _resolve_conflicts(db, employee_id, day, start, end)
            db.add(AvailabilityRules(
                employee_id=employee_id,
                day_of_week=day,
                start_time_local=start,
                end_time_local=end,
                rule_type=rule_type,
                active=True,
            ))
            _merge_adjacent_same_type(db, employee_id, day)


def _merge_adjacent_coverage(db: Session, store_id: int, department_id: int, day: int) -> None:
    """Merge adjacent coverage rules that have identical staff counts."""
    db.flush()
    rules = db.query(CoverageRequirements).filter(
        CoverageRequirements.store_id == store_id,
        CoverageRequirements.department_id == department_id,
        CoverageRequirements.day_of_week == day,
        CoverageRequirements.active == True,
    ).all()

    if len(rules) < 2:
        return

    def _start(r: CoverageRequirements) -> int:
        return 0 if r.start_time_local is None else r.start_time_local.hour * 60 + r.start_time_local.minute

    def _end(r: CoverageRequirements) -> int:
        return 1440 if r.end_time_local is None else r.end_time_local.hour * 60 + r.end_time_local.minute

    sorted_rules = sorted(rules, key=_start)
    i = 0
    while i < len(sorted_rules) - 1:
        cur = sorted_rules[i]
        nxt = sorted_rules[i + 1]
        if (cur.min_staff == nxt.min_staff and cur.max_staff == nxt.max_staff
                and _end(cur) == _start(nxt)):
            cur.end_time_local = nxt.end_time_local
            nxt.active = False
            sorted_rules.pop(i + 1)
        else:
            i += 1


def _merge_adjacent_role_requirements(db: Session, store_id: int, department_id: Optional[int], day: Optional[int]) -> None:
    """Merge adjacent role requirement rules with identical role flags."""
    db.flush()
    query = db.query(RoleRequirements).filter(
        RoleRequirements.store_id == store_id,
        RoleRequirements.active == True,
    )
    if department_id is not None:
        query = query.filter(RoleRequirements.department_id == department_id)
    if day is None:
        query = query.filter(RoleRequirements.day_of_week.is_(None))
    else:
        query = query.filter(RoleRequirements.day_of_week == day)
    rules = query.all()

    if len(rules) < 2:
        return

    def _start(r: RoleRequirements) -> int:
        return 0 if r.start_time_local is None else r.start_time_local.hour * 60 + r.start_time_local.minute

    def _end(r: RoleRequirements) -> int:
        return 1440 if r.end_time_local is None else r.end_time_local.hour * 60 + r.end_time_local.minute

    sorted_rules = sorted(rules, key=_start)
    i = 0
    while i < len(sorted_rules) - 1:
        cur = sorted_rules[i]
        nxt = sorted_rules[i + 1]
        if (cur.requires_keyholder == nxt.requires_keyholder
                and cur.requires_manager == nxt.requires_manager
                and cur.min_manager_count == nxt.min_manager_count
                and _end(cur) == _start(nxt)):
            cur.end_time_local = nxt.end_time_local
            nxt.active = False
            sorted_rules.pop(i + 1)
        else:
            i += 1


def _apply_coverage_changes(db: Session, result: dict, approved_by: int) -> None:
    """Apply coverage requirement changes."""
    store_id = result["store_id"]
    department_id = result["department_id"]
    changes = result.get("changes", [])

    for change in changes:
        action = change["action"]

        if action == "ADD":
            day = change["day_of_week"]
            req = CoverageRequirements(
                store_id=store_id,
                department_id=department_id,
                day_of_week=day,
                start_time_local=_parse_time(change["start_time"]),
                end_time_local=_parse_time(change["end_time"]),
                min_staff=change["min_staff"],
                max_staff=change.get("max_staff"),
                active=True,
                last_modified_by_user_id=approved_by,
            )
            db.add(req)
            _merge_adjacent_coverage(db, store_id, department_id, day)

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
                    _merge_adjacent_coverage(db, store_id, department_id, req.day_of_week)


def _apply_role_requirement_changes(db: Session, result: dict, approved_by: int) -> None:
    """Apply role requirement changes."""
    store_id = result["store_id"]
    department_id = result.get("department_id")
    changes = result.get("changes", [])

    for change in changes:
        action = change["action"]

        if action == "ADD":
            day = change.get("day_of_week")
            req = RoleRequirements(
                store_id=store_id,
                department_id=department_id,
                day_of_week=day,
                start_time_local=_parse_time(change["start_time"]),
                end_time_local=_parse_time(change["end_time"]),
                requires_keyholder=change.get("requires_keyholder", False),
                requires_manager=change.get("requires_manager", False),
                min_manager_count=change.get("min_manager_count", 0),
                active=True,
            )
            db.add(req)
            _merge_adjacent_role_requirements(db, store_id, department_id, day)

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
                    _merge_adjacent_role_requirements(db, store_id, department_id, req.day_of_week)