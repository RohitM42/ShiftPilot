"""
Availability checking utilities.
Determines if an employee can work a given time slot.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional

from .types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    TimeOffRequest,
    Shift,
)


def times_overlap(
    start1: time, end1: time,
    start2: time, end2: time
) -> bool:
    """Check if two time ranges overlap (same day)."""
    return start1 < end2 and start2 < end1


def datetime_ranges_overlap(
    start1: datetime, end1: datetime,
    start2: datetime, end2: datetime
) -> bool:
    """Check if two datetime ranges overlap."""
    return start1 < end2 and start2 < end1


def is_employee_on_time_off(
    employee_id: int,
    shift_start: datetime,
    shift_end: datetime,
    time_off_requests: list[TimeOffRequest]
) -> bool:
    """Check if employee has approved time off during shift period."""
    for req in time_off_requests:
        if req.employee_id != employee_id:
            continue
        if datetime_ranges_overlap(shift_start, shift_end, req.start_datetime, req.end_datetime):
            return True
    return False


def get_availability_for_slot(
    employee_id: int,
    day_of_week: int,
    slot_start: time,
    slot_end: time,
    rules: list[AvailabilityRule]
) -> Optional[AvailabilityType]:
    """
    Get the effective availability type for an employee on a specific day/time slot.
    
    Returns:
        AvailabilityType if there's a matching rule, None if no rules apply
        (no rules = assumed available by default)
    """
    employee_rules = [r for r in rules if r.employee_id == employee_id and r.day_of_week == day_of_week]
    
    if not employee_rules:
        return None  # No rules = default available
    
    # Check for UNAVAILABLE rules first (highest priority for blocking)
    for rule in employee_rules:
        if rule.rule_type == AvailabilityType.UNAVAILABLE:
            # All-day unavailable
            if rule.start_time is None and rule.end_time is None:
                return AvailabilityType.UNAVAILABLE
            # Time-specific unavailable - check overlap
            if rule.start_time and rule.end_time:
                if times_overlap(slot_start, slot_end, rule.start_time, rule.end_time):
                    return AvailabilityType.UNAVAILABLE
    
    # Check for AVAILABLE rules
    for rule in employee_rules:
        if rule.rule_type == AvailabilityType.AVAILABLE:
            # All-day available
            if rule.start_time is None and rule.end_time is None:
                # Check if also preferred during this time
                for pref_rule in employee_rules:
                    if pref_rule.rule_type == AvailabilityType.PREFERRED:
                        if pref_rule.start_time and pref_rule.end_time:
                            if times_overlap(slot_start, slot_end, pref_rule.start_time, pref_rule.end_time):
                                return AvailabilityType.PREFERRED
                return AvailabilityType.AVAILABLE
            # Time-specific available - check if slot fits within
            if rule.start_time and rule.end_time:
                if slot_start >= rule.start_time and slot_end <= rule.end_time:
                    # Check if also preferred
                    for pref_rule in employee_rules:
                        if pref_rule.rule_type == AvailabilityType.PREFERRED:
                            if pref_rule.start_time and pref_rule.end_time:
                                if times_overlap(slot_start, slot_end, pref_rule.start_time, pref_rule.end_time):
                                    return AvailabilityType.PREFERRED
                    return AvailabilityType.AVAILABLE
    
    # Check for PREFERRED only (implies available)
    for rule in employee_rules:
        if rule.rule_type == AvailabilityType.PREFERRED:
            if rule.start_time is None and rule.end_time is None:
                return AvailabilityType.PREFERRED
            if rule.start_time and rule.end_time:
                if times_overlap(slot_start, slot_end, rule.start_time, rule.end_time):
                    return AvailabilityType.PREFERRED
    
    # Has rules but none match this slot - if they have AVAILABLE rules elsewhere, 
    # this slot is implicitly unavailable
    has_available_rules = any(r.rule_type == AvailabilityType.AVAILABLE for r in employee_rules)
    if has_available_rules:
        return AvailabilityType.UNAVAILABLE
    
    return None


def can_employee_work_shift(
    employee: Employee,
    shift_start: datetime,
    shift_end: datetime,
    department_id: int,
    availability_rules: list[AvailabilityRule],
    time_off_requests: list[TimeOffRequest],
    existing_shifts: list[Shift],
) -> tuple[bool, str]:
    """
    Check if an employee can work a specific shift.
    """
    # Check department assignment
    if department_id not in employee.department_ids:
        return False, f"Employee not assigned to department {department_id}"
    
    # Check time off
    if is_employee_on_time_off(employee.id, shift_start, shift_end, time_off_requests):
        return False, "Employee has approved time off"
    
    # Check availability rules
    day_of_week = shift_start.weekday()
    availability = get_availability_for_slot(
        employee.id,
        day_of_week,
        shift_start.time(),
        shift_end.time(),
        availability_rules
    )
    
    if availability == AvailabilityType.UNAVAILABLE:
        return False, "Employee unavailable during this time"
    
    # Check for shift conflicts (double booking)
    for existing in existing_shifts:
        if existing.employee_id != employee.id:
            continue
        if datetime_ranges_overlap(shift_start, shift_end, existing.start_datetime, existing.end_datetime):
            return False, "Conflicts with existing shift"
    
    return True, "OK"


def get_available_employees_for_slot(
    employees: list[Employee],
    shift_start: datetime,
    shift_end: datetime,
    department_id: int,
    availability_rules: list[AvailabilityRule],
    time_off_requests: list[TimeOffRequest],
    existing_shifts: list[Shift],
) -> list[tuple[Employee, AvailabilityType]]:
    """
    Get all employees who can work a specific shift slot.
    
    Returns:
        List of (employee, availability_type) tuples, sorted by preference:
        - PREFERRED first
        - AVAILABLE second  
        - None (default available) last
    """
    available = []
    
    for emp in employees:
        can_work, _ = can_employee_work_shift(
            emp,
            shift_start,
            shift_end,
            department_id,
            availability_rules,
            time_off_requests,
            existing_shifts,
        )
        
        if can_work:
            avail_type = get_availability_for_slot(
                emp.id,
                shift_start.weekday(),
                shift_start.time(),
                shift_end.time(),
                availability_rules
            )
            available.append((emp, avail_type))
    
    # Sort: PREFERRED > AVAILABLE > None
    def sort_key(item: tuple[Employee, Optional[AvailabilityType]]) -> int:
        avail = item[1]
        if avail == AvailabilityType.PREFERRED:
            return 0
        elif avail == AvailabilityType.AVAILABLE:
            return 1
        else:
            return 2
    
    return sorted(available, key=sort_key)