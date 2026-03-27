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
from app.db.models.users import Users
from app.api.deps import check_store_access


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

    # For scheduling rule changes, validate the approver has access to the target store
    if intent_type in ("COVERAGE", "ROLE_REQUIREMENT"):
        store_id_in_result = result.get("store_id")
        if store_id_in_result:
            approver = db.query(Users).filter(Users.id == approved_by_user_id).first()
            if approver and not check_store_access(db, approver, store_id_in_result):
                raise ApprovalError("Approver does not have access to the target store")

    handler(db, result, approved_by_user_id)


def _parse_time(t: Optional[str]) -> Optional[time]:
    """Parse HH:MM string to time object."""
    if not t:
        return None
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


def _start_mins(t: Optional[time]) -> int:
    """Convert a start time to minutes since midnight. None = 0 (start of day)."""
    return 0 if t is None else t.hour * 60 + t.minute


def _end_mins(t: Optional[time]) -> int:
    """Convert an end time to minutes since midnight. None or 00:00 = 1440 (end of day)."""
    if t is None:
        return 1440
    mins = t.hour * 60 + t.minute
    return 1440 if mins == 0 else mins


def _times_overlap(
    new_start: Optional[time],
    new_end: Optional[time],
    ex_start: Optional[time],
    ex_end: Optional[time],
) -> bool:
    """Return True if two time ranges overlap. None means all-day (00:00–24:00)."""
    ns = _start_mins(new_start)
    ne = _end_mins(new_end)
    es = _start_mins(ex_start)
    ee = _end_mins(ex_end)
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

    ns = _start_mins(new_start)
    ne = _end_mins(new_end)

    for ex in existing:
        es = _start_mins(ex.start_time_local)
        ee = _end_mins(ex.end_time_local)

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

    sorted_rules = sorted(rules, key=lambda r: _start_mins(r.start_time_local))

    i = 0
    while i < len(sorted_rules) - 1:
        cur = sorted_rules[i]
        nxt = sorted_rules[i + 1]
        if cur.rule_type == nxt.rule_type and _end_mins(cur.end_time_local) == _start_mins(nxt.start_time_local):
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


def _add_or_reactivate_coverage(
    db: Session,
    store_id: int,
    department_id: int,
    day: int,
    start: Optional[time],
    end: Optional[time],
    min_staff: int,
    max_staff: Optional[int],
    approved_by: int,
) -> None:
    """
    Insert a coverage rule, or reactivate+update an existing inactive one if the
    unique key (store, dept, day, start, end) already exists. Avoids UniqueViolation
    when the same time range was previously deactivated.
    """
    db.flush()  # commit pending deactivations before querying
    existing = db.query(CoverageRequirements).filter(
        CoverageRequirements.store_id == store_id,
        CoverageRequirements.department_id == department_id,
        CoverageRequirements.day_of_week == day,
        CoverageRequirements.start_time_local == start,
        CoverageRequirements.end_time_local == end,
    ).first()
    if existing:
        existing.active = True
        existing.min_staff = min_staff
        existing.max_staff = max_staff
        existing.last_modified_by_user_id = approved_by
    else:
        db.add(CoverageRequirements(
            store_id=store_id,
            department_id=department_id,
            day_of_week=day,
            start_time_local=start,
            end_time_local=end,
            min_staff=min_staff,
            max_staff=max_staff,
            active=True,
            last_modified_by_user_id=approved_by,
        ))


def _resolve_conflicts_coverage(
    db: Session,
    store_id: int,
    department_id: int,
    day: int,
    new_start: Optional[time],
    new_end: Optional[time],
    approved_by: int,
) -> None:
    """
    For every active coverage rule on this day that overlaps the new time range,
    trim, split, or deactivate it so there are no overlapping windows.
    Preserves min_staff/max_staff on trimmed pieces.
    """
    existing = db.query(CoverageRequirements).filter(
        CoverageRequirements.store_id == store_id,
        CoverageRequirements.department_id == department_id,
        CoverageRequirements.day_of_week == day,
        CoverageRequirements.active == True,
    ).all()

    ns = _start_mins(new_start)
    ne = _end_mins(new_end)

    for ex in existing:
        es = _start_mins(ex.start_time_local)
        ee = _end_mins(ex.end_time_local)

        if not (ns < ee and ne > es):
            continue  # no overlap

        # New rule completely covers existing → deactivate
        if ns <= es and ne >= ee:
            ex.active = False
            ex.last_modified_by_user_id = approved_by

        # New rule overlaps only the start of existing → trim start forward
        elif ns <= es and ne < ee:
            ex.active = False
            ex.last_modified_by_user_id = approved_by
            _add_or_reactivate_coverage(db, store_id, department_id, day, new_end, ex.end_time_local, ex.min_staff, ex.max_staff, approved_by)

        # New rule overlaps only the end of existing → trim end backward
        elif ns > es and ne >= ee:
            ex.active = False
            ex.last_modified_by_user_id = approved_by
            _add_or_reactivate_coverage(db, store_id, department_id, day, ex.start_time_local, new_start, ex.min_staff, ex.max_staff, approved_by)

        # New rule is inside existing → split into two
        else:
            ex.active = False
            ex.last_modified_by_user_id = approved_by
            _add_or_reactivate_coverage(db, store_id, department_id, day, ex.start_time_local, new_start, ex.min_staff, ex.max_staff, approved_by)
            _add_or_reactivate_coverage(db, store_id, department_id, day, new_end, ex.end_time_local, ex.min_staff, ex.max_staff, approved_by)


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
        if cur.min_staff == nxt.min_staff and _end(cur) == _start(nxt):
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
            new_start = _parse_time(change["start_time"])
            new_end = _parse_time(change["end_time"])
            _resolve_conflicts_coverage(db, store_id, department_id, day, new_start, new_end, approved_by)
            _add_or_reactivate_coverage(db, store_id, department_id, day, new_start, new_end, change["min_staff"], change.get("max_staff"), approved_by)
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
            start = _parse_time(change["start_time"])
            end = _parse_time(change["end_time"])
            requires_keyholder = change.get("requires_keyholder", False)
            requires_manager = change.get("requires_manager", False)
            min_manager_count = change.get("min_manager_count", 0)
            db.flush()
            existing_rr = db.query(RoleRequirements).filter(
                RoleRequirements.store_id == store_id,
                RoleRequirements.department_id == department_id,
                RoleRequirements.day_of_week == day,
                RoleRequirements.start_time_local == start,
                RoleRequirements.end_time_local == end,
            ).first()
            if existing_rr:
                existing_rr.active = True
                existing_rr.requires_keyholder = requires_keyholder
                existing_rr.requires_manager = requires_manager
                existing_rr.min_manager_count = min_manager_count
            else:
                db.add(RoleRequirements(
                    store_id=store_id,
                    department_id=department_id,
                    day_of_week=day,
                    start_time_local=start,
                    end_time_local=end,
                    requires_keyholder=requires_keyholder,
                    requires_manager=requires_manager,
                    min_manager_count=min_manager_count,
                    active=True,
                ))
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