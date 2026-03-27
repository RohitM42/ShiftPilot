"""
Constraint checking utilities for schedule validation.
Handles coverage requirements, role requirements, and contracted hours. ***budget constraint to be added***
"""

from datetime import datetime, date, time, timedelta
from typing import Optional

from .types import (
    Employee,
    Shift,
    CoverageRequirement,
    RoleRequirement,
    ScheduleContext,
)
from .availability import datetime_ranges_overlap, times_overlap


def get_shifts_covering_time(
    shifts: list[Shift],
    target_datetime: datetime,
    department_id: Optional[int] = None
) -> list[Shift]:
    """Get all shifts that are active at a specific datetime."""
    covering = []
    for shift in shifts:
        if shift.start_datetime <= target_datetime < shift.end_datetime:
            if department_id is None or shift.department_id == department_id:
                covering.append(shift)
    return covering


def get_shifts_in_window(
    shifts: list[Shift],
    start_dt: datetime,
    end_dt: datetime,
    department_id: Optional[int] = None
) -> list[Shift]:
    """Get all shifts that overlap with a time window."""
    overlapping = []
    for shift in shifts:
        if datetime_ranges_overlap(shift.start_datetime, shift.end_datetime, start_dt, end_dt):
            if department_id is None or shift.department_id == department_id:
                overlapping.append(shift)
    return overlapping


def check_coverage_at_time(
    shifts: list[Shift],
    employees: list[Employee],
    requirement: CoverageRequirement,
    check_datetime: datetime
) -> tuple[bool, int, int]:
    """
    Check if coverage requirement is met at a specific datetime.
    """
    covering_shifts = get_shifts_covering_time(
        shifts, check_datetime, requirement.department_id
    )
    current_count = len(covering_shifts)
    return current_count >= requirement.min_staff, current_count, requirement.min_staff


def check_coverage_for_window(
    shifts: list[Shift],
    employees: list[Employee],
    requirement: CoverageRequirement,
    week_start: date
) -> tuple[bool, list[datetime]]:
    """
    Check if coverage requirement is met throughout its entire window.
    Samples at 30-minute intervals to find gaps.
    """
    slot_date = week_start + timedelta(days=requirement.day_of_week)
    start_dt = datetime.combine(slot_date, requirement.start_time)
    end_dt = datetime.combine(slot_date, requirement.end_time)
    
    gaps = []
    current = start_dt
    interval = timedelta(minutes=30)
    
    while current < end_dt:
        is_met, _, _ = check_coverage_at_time(shifts, employees, requirement, current)
        if not is_met:
            gaps.append(current)
        current += interval
    
    return len(gaps) == 0, gaps


def check_role_requirement_at_time(
    shifts: list[Shift],
    employees: list[Employee],
    requirement: RoleRequirement,
    check_datetime: datetime
) -> tuple[bool, str]:
    """
    Check if role requirement is met at a specific datetime.
    """
    # Get shifts active at this time (for the relevant department or whole store)
    if requirement.department_id:
        active_shifts = get_shifts_covering_time(shifts, check_datetime, requirement.department_id)
    else:
        active_shifts = get_shifts_covering_time(shifts, check_datetime)
    
    # Map shifts to employees
    emp_map = {e.id: e for e in employees}
    active_employees = [emp_map[s.employee_id] for s in active_shifts if s.employee_id in emp_map]
    
    # Check keyholder requirement
    if requirement.requires_keyholder:
        has_keyholder = any(e.is_keyholder for e in active_employees)
        if not has_keyholder:
            return False, "No keyholder present"
    
    # Check manager requirement
    if requirement.requires_manager:
        manager_count = sum(1 for e in active_employees if e.is_manager)
        if manager_count < requirement.min_manager_count:
            return False, f"Need {requirement.min_manager_count} manager(s), have {manager_count}"
    
    return True, "OK"


def check_role_requirement_for_window(
    shifts: list[Shift],
    employees: list[Employee],
    requirement: RoleRequirement,
    week_start: date
) -> tuple[bool, list[datetime]]:
    """
    Check if role requirement is met throughout its window.
    """
    # Determine which days this applies to
    if requirement.day_of_week is not None:
        days = [requirement.day_of_week]
    else:
        days = list(range(7))  # All days
    
    gaps = []
    interval = timedelta(minutes=30)
    
    for day in days:
        slot_date = week_start + timedelta(days=day)
        start_dt = datetime.combine(slot_date, requirement.start_time)
        end_dt = datetime.combine(slot_date, requirement.end_time)
        
        current = start_dt
        while current < end_dt:
            is_met, _ = check_role_requirement_at_time(shifts, employees, requirement, current)
            if not is_met:
                gaps.append(current)
            current += interval
    
    return len(gaps) == 0, gaps


def calculate_employee_hours(shifts: list[Shift], employee_id: int) -> float:
    """Calculate total hours assigned to an employee."""
    return sum(s.duration_hours for s in shifts if s.employee_id == employee_id)


def check_contracted_hours(
    shifts: list[Shift],
    employees: list[Employee]
) -> dict[int, float]:
    """
    Check if all employees meet their contracted hours.
    
    Returns:
        employee_id -> shortfall (positive = under contracted, 0 = met or exceeded)
    """
    shortfalls = {}
    
    for emp in employees:
        assigned = calculate_employee_hours(shifts, emp.id)
        shortfall = emp.contracted_weekly_hours - assigned
        if shortfall > 0:
            shortfalls[emp.id] = shortfall
    
    return shortfalls


def validate_schedule(context: ScheduleContext, shifts: list[Shift]) -> dict:
    """
    Validate a complete schedule against all constraints.
    
    Returns:
        {
            'valid': bool,
            'coverage_gaps': [(requirement, [gap_times])],
            'role_gaps': [(requirement, [gap_times])],
            'hour_shortfalls': {employee_id: shortfall},
        }
    """
    coverage_gaps = []
    for req in context.coverage_requirements:
        is_met, gaps = check_coverage_for_window(
            shifts, context.employees, req, context.week_start
        )
        if not is_met:
            coverage_gaps.append((req, gaps))
    
    role_gaps = []
    for req in context.role_requirements:
        is_met, gaps = check_role_requirement_for_window(
            shifts, context.employees, req, context.week_start
        )
        if not is_met:
            role_gaps.append((req, gaps))
    
    hour_shortfalls = check_contracted_hours(shifts, context.employees)
    
    return {
        'valid': len(coverage_gaps) == 0 and len(role_gaps) == 0 and len(hour_shortfalls) == 0,
        'coverage_gaps': coverage_gaps,
        'role_gaps': role_gaps,
        'hour_shortfalls': hour_shortfalls,
    }