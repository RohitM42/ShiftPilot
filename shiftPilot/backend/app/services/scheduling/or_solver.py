"""
OR-Tools CP-SAT based schedule solver.

Constraint Priority (via weights):
- Coverage requirements: highest priority (soft, weight -1000 per unmet slot)
- Role requirements: highest priority (soft, weight -1000 per unmet slot)  
- Contracted hours: high priority (soft, weight -100 per hour short)
- Overtime: low priority (soft, weight -3 per hour over)
- Primary department preference: bonus +25
- Non-primary department: penalty -15
- Preferred availability: bonus +15
- Standard shift lengths: bonus +10/+8/+7/+5
"""

from datetime import datetime, date, time, timedelta
from typing import Optional
from ortools.sat.python import cp_model

from .types import (
    Employee,
    Shift,
    CoverageRequirement,
    RoleRequirement,
    AvailabilityRule,
    AvailabilityType,
    ScheduleContext,
    ScheduleResult,
)
from .availability import (
    get_availability_for_slot,
    is_employee_on_time_off,
    datetime_ranges_overlap,
)


# Time constants
SLOT_DURATION_MINUTES = 60 # 1h for speed right now but may need to lower to 30 for better constraint handling (assumption that constraint times fall on the hour)
###ALSO Note FOR MORE COMPLEX SEED DATA, IT MAY NEED TO CHANGE BACK TO 30, CURRENTLY NO SHIFTS CAN START AT XX:30###
SLOTS_PER_HOUR = 60 // SLOT_DURATION_MINUTES
DAY_START_HOUR = 6 # 6am for now but can be made configurable
DAY_END_HOUR = 22
SLOTS_PER_DAY = (DAY_END_HOUR - DAY_START_HOUR) * SLOTS_PER_HOUR

# Shift length constants
MIN_SHIFT_HOURS = 4
MAX_REGULAR_HOURS = 9
MAX_MANAGER_HOURS = 12
MIN_REST_HOURS = 12

# Soft constraint weights (negative = penalty, positive = bonus)
WEIGHT_UNMET_COVERAGE_SLOT = -1000
WEIGHT_UNMET_ROLE_SLOT = -1000
WEIGHT_UNMET_CONTRACTED_HOUR = -100  # per hour short
WEIGHT_OVERTIME_HOUR = -3  # per hour over
WEIGHT_PRIMARY_DEPT = 25
WEIGHT_NON_PRIMARY_DEPT = -15
WEIGHT_PREFERRED_AVAIL = 15
WEIGHT_SHIFT_8H = 10
WEIGHT_SHIFT_6H = 8
WEIGHT_SHIFT_4H = 7
WEIGHT_SHIFT_OTHER = 5


def slot_to_time(slot: int) -> time:
    """Convert slot index to time. Slot 0 = 6:00am."""
    total_minutes = DAY_START_HOUR * 60 + slot * SLOT_DURATION_MINUTES
    return time(total_minutes // 60, total_minutes % 60)


def time_to_slot(t: time) -> int:
    """Convert time to slot index."""
    total_minutes = t.hour * 60 + t.minute
    start_minutes = DAY_START_HOUR * 60
    return (total_minutes - start_minutes) // SLOT_DURATION_MINUTES


def get_valid_shift_lengths(is_manager: bool) -> list[int]:
    """Get valid shift lengths in slots for employee type."""
    max_hours = MAX_MANAGER_HOURS if is_manager else MAX_REGULAR_HOURS
    min_slots = MIN_SHIFT_HOURS * SLOTS_PER_HOUR
    max_slots = max_hours * SLOTS_PER_HOUR
    # Only allow shifts starting on the hour (2 slots for 30-min granularity) for now, may change later 
    return list(range(min_slots, max_slots + 1, SLOTS_PER_HOUR))


def _get_shift_length_bonus(length_slots: int) -> int:
    """Get bonus for shift length preference."""
    hours = length_slots // SLOTS_PER_HOUR
    if hours == 8:
        return WEIGHT_SHIFT_8H
    elif hours == 6:
        return WEIGHT_SHIFT_6H
    elif hours == 4:
        return WEIGHT_SHIFT_4H
    else:
        return WEIGHT_SHIFT_OTHER


def _build_availability_matrix(
    employee: Employee,
    context: ScheduleContext,
) -> tuple[list[list[bool]], list[list[bool]]]:
    """
    Build availability matrices for an employee.
    Returns:
        (available_matrix, preferred_matrix) - both 7 x SLOTS_PER_DAY
    """
    available = [[False] * SLOTS_PER_DAY for _ in range(7)]
    preferred = [[False] * SLOTS_PER_DAY for _ in range(7)]
    
    for day in range(7):
        slot_date = context.week_start + timedelta(days=day)
        
        for slot in range(SLOTS_PER_DAY):
            slot_start = slot_to_time(slot)
            slot_end = slot_to_time(slot + 1)
            
            # Check availability rules
            avail = get_availability_for_slot(
                employee.id, day, slot_start, slot_end,
                context.availability_rules
            )
            
            if avail == AvailabilityType.UNAVAILABLE:
                continue
            
            # Check time off
            slot_start_dt = datetime.combine(slot_date, slot_start)
            slot_end_dt = datetime.combine(slot_date, slot_end)
            
            if is_employee_on_time_off(
                employee.id, slot_start_dt, slot_end_dt, context.time_off_requests
            ):
                continue
            
            # Check conflicts with existing shifts
            has_conflict = False
            for existing in context.existing_shifts:
                if existing.employee_id != employee.id:
                    continue
                if datetime_ranges_overlap(
                    slot_start_dt, slot_end_dt,
                    existing.start_datetime, existing.end_datetime
                ):
                    has_conflict = True
                    break
            
            if not has_conflict:
                available[day][slot] = True
                if avail == AvailabilityType.PREFERRED:
                    preferred[day][slot] = True
    
    return available, preferred


def _get_existing_hours(employee_id: int, existing_shifts: list[Shift]) -> float:
    """Calculate hours already assigned from existing shifts."""
    return sum(
        s.duration_hours for s in existing_shifts
        if s.employee_id == employee_id
    )


def _get_existing_days(employee_id: int, existing_shifts: list[Shift]) -> set[int]:
    """Get days employee already has shifts."""
    return {s.day_of_week for s in existing_shifts if s.employee_id == employee_id}


def solve_schedule(context: ScheduleContext) -> ScheduleResult:
    """Main entry point for OR-Tools schedule generation."""
    model = cp_model.CpModel()
    
    employees = context.employees
    emp_map = {e.id: e for e in employees}
    
    # Pre-compute availability and preference matrices
    availability = {}
    preferred = {}
    for emp in employees:
        availability[emp.id], preferred[emp.id] = _build_availability_matrix(emp, context)
    
    existing_hours = {e.id: _get_existing_hours(e.id, context.existing_shifts) for e in employees}
    existing_days = {e.id: _get_existing_days(e.id, context.existing_shifts) for e in employees}
    
    # ========== DECISION VARIABLES ==========
    # shift_vars[(emp_id, day, start_slot, length, dept_id)] = BoolVar
    shift_vars = {}
    
    for emp in employees:
        valid_lengths = get_valid_shift_lengths(emp.is_manager)
        avail = availability[emp.id]
        
        for day in range(7):
            # Skip days with existing shifts
            if day in existing_days[emp.id]:
                continue
                
            for start_slot in range(SLOTS_PER_DAY):
                for length in valid_lengths:
                    end_slot = start_slot + length
                    if end_slot > SLOTS_PER_DAY:
                        continue
                    
                    # Check all slots in shift are available
                    if not all(avail[day][s] for s in range(start_slot, end_slot)):
                        continue
                    
                    # Create a variable for each valid department
                    for dept_id in emp.department_ids:
                        var_name = f"shift_e{emp.id}_d{day}_s{start_slot}_l{length}_dept{dept_id}"
                        shift_vars[(emp.id, day, start_slot, length, dept_id)] = model.NewBoolVar(var_name)
    
    # Helper functions
    def get_emp_day_shifts(emp_id: int, day: int):
        return [(key, var) for key, var in shift_vars.items() 
                if key[0] == emp_id and key[1] == day]
    
    # Helper: check if a shift covers a specific slot
    def shift_covers_slot(key: tuple, slot: int) -> bool:
        _, _, start, length, _ = key
        return start <= slot < start + length
    
    # ========== HARD CONSTRAINTS ==========
    
    # 1. One shift per day per employee (across all departments)
    for emp in employees:
        for day in range(7):
            if day in existing_days[emp.id]:
                continue
            day_shifts = get_emp_day_shifts(emp.id, day)
            if day_shifts:
                model.AddAtMostOne([var for _, var in day_shifts])
    
    # 2. 12-hour rest between consecutive days
    for emp in employees:
        for day in range(6):
            today_shifts = get_emp_day_shifts(emp.id, day)
            tomorrow_shifts = get_emp_day_shifts(emp.id, day + 1)
            
            # Also check existing shifts
            existing_today = [s for s in context.existing_shifts 
                           if s.employee_id == emp.id and s.day_of_week == day]
            existing_tomorrow = [s for s in context.existing_shifts 
                               if s.employee_id == emp.id and s.day_of_week == day + 1]
            
            # New shift today vs new shift tomorrow
            for (key1, var1) in today_shifts:
                _, _, start1, length1, _ = key1
                end_slot1 = start1 + length1
                end_minutes = DAY_START_HOUR * 60 + end_slot1 * SLOT_DURATION_MINUTES
                
                for (key2, var2) in tomorrow_shifts:
                    _, _, start2, _, _ = key2
                    start_minutes = DAY_START_HOUR * 60 + start2 * SLOT_DURATION_MINUTES
                    rest_minutes = (24 * 60 - end_minutes) + start_minutes
                    
                    if rest_minutes < MIN_REST_HOURS * 60:
                        model.Add(var1 + var2 <= 1)
            
            # Existing shift today vs new shift tomorrow
            for existing in existing_today:
                end_minutes = existing.end_datetime.hour * 60 + existing.end_datetime.minute
                for (key2, var2) in tomorrow_shifts:
                    _, _, start2, _, _ = key2
                    start_minutes = DAY_START_HOUR * 60 + start2 * SLOT_DURATION_MINUTES
                    rest_minutes = (24 * 60 - end_minutes) + start_minutes
                    if rest_minutes < MIN_REST_HOURS * 60:
                        model.Add(var2 == 0)
            
            # New shift today vs existing shift tomorrow
            for existing in existing_tomorrow:
                start_minutes = existing.start_datetime.hour * 60 + existing.start_datetime.minute
                for (key1, var1) in today_shifts:
                    _, _, start1, length1, _ = key1
                    end_slot1 = start1 + length1
                    end_minutes = DAY_START_HOUR * 60 + end_slot1 * SLOT_DURATION_MINUTES
                    rest_minutes = (24 * 60 - end_minutes) + start_minutes
                    if rest_minutes < MIN_REST_HOURS * 60:
                        model.Add(var1 == 0)
    
    # ========== SOFT CONSTRAINTS (Objective Terms) ==========
    objective_terms = []
    
    # 3. Coverage requirements (soft - high penalty for unmet)
    coverage_slack_vars = []  # Track for reporting
    for req in context.coverage_requirements:
        dept_id = req.department_id
        day = req.day_of_week
        req_start_slot = time_to_slot(req.start_time)
        req_end_slot = time_to_slot(req.end_time)
        
        for slot in range(req_start_slot, req_end_slot):
            covering_vars = []
            
            # Count existing shifts covering this slot
            existing_coverage = 0
            slot_time = slot_to_time(slot)
            slot_dt = datetime.combine(
                context.week_start + timedelta(days=day), slot_time
            )
            for s in context.existing_shifts:
                if s.department_id == dept_id and s.start_datetime <= slot_dt < s.end_datetime:
                    existing_coverage += 1
            
            # Find new shift vars that cover this slot
            for emp in employees:
                if dept_id not in emp.department_ids:
                    continue
                for key, var in shift_vars.items():
                    emp_id, shift_day, start, length, shift_dept = key
                    if emp_id != emp.id or shift_day != day or shift_dept != dept_id:
                        continue
                    if shift_covers_slot(key, slot):
                        covering_vars.append(var)
            
            needed = req.min_staff - existing_coverage
            if needed > 0:
                if covering_vars:
                    # Slack variable for unmet coverage
                    slack = model.NewIntVar(0, needed, f"cov_slack_d{day}_s{slot}_dept{dept_id}")
                    model.Add(sum(covering_vars) + slack >= needed)
                    objective_terms.append(WEIGHT_UNMET_COVERAGE_SLOT * slack)
                    coverage_slack_vars.append((req, slot, slack))
                else:
                    # No possible coverage - add constant penalty
                    objective_terms.append(WEIGHT_UNMET_COVERAGE_SLOT * needed)
    
    # 4. Role requirements (soft - high penalty for unmet)
    role_slack_vars = []
    for req in context.role_requirements:
        days = [req.day_of_week] if req.day_of_week is not None else list(range(7))
        req_start_slot = time_to_slot(req.start_time)
        req_end_slot = time_to_slot(req.end_time)
        
        for day in days:
            for slot in range(req_start_slot, req_end_slot):
                slot_time = slot_to_time(slot)
                slot_dt = datetime.combine(
                    context.week_start + timedelta(days=day), slot_time
                )
                
                # Check existing coverage
                existing_keyholders = 0
                existing_managers = 0
                for s in context.existing_shifts:
                    if s.start_datetime <= slot_dt < s.end_datetime:
                        emp = emp_map.get(s.employee_id)
                        if emp:
                            if emp.is_keyholder:
                                existing_keyholders += 1
                            if emp.is_manager:
                                existing_managers += 1
                
                if req.requires_keyholder and existing_keyholders == 0:
                    keyholder_vars = []
                    for emp in employees:
                        if not emp.is_keyholder:
                            continue
                        for key, var in shift_vars.items():
                            emp_id, shift_day, start, length, _ = key
                            if emp_id != emp.id or shift_day != day:
                                continue
                            if shift_covers_slot(key, slot):
                                keyholder_vars.append(var)
                    
                    if keyholder_vars:
                        slack = model.NewBoolVar(f"role_key_slack_d{day}_s{slot}")
                        model.Add(sum(keyholder_vars) + slack >= 1)
                        objective_terms.append(WEIGHT_UNMET_ROLE_SLOT * slack)
                        role_slack_vars.append((req, day, slot, 'keyholder', slack))
                    else:
                        objective_terms.append(WEIGHT_UNMET_ROLE_SLOT)
                
                if req.requires_manager:
                    needed_managers = req.min_manager_count - existing_managers
                    if needed_managers > 0:
                        manager_vars = []
                        for emp in employees:
                            if not emp.is_manager:
                                continue
                            for key, var in shift_vars.items():
                                emp_id, shift_day, start, length, _ = key
                                if emp_id != emp.id or shift_day != day:
                                    continue
                                if shift_covers_slot(key, slot):
                                    manager_vars.append(var)
                        
                        if manager_vars:
                            slack = model.NewIntVar(0, needed_managers, f"role_mgr_slack_d{day}_s{slot}")
                            model.Add(sum(manager_vars) + slack >= needed_managers)
                            objective_terms.append(WEIGHT_UNMET_ROLE_SLOT * slack)
                            role_slack_vars.append((req, day, slot, 'manager', slack))
                        else:
                            objective_terms.append(WEIGHT_UNMET_ROLE_SLOT * needed_managers)
    
    # 5. Contracted hours (soft - penalty for shortfall)
    hour_shortfall_vars = {}
    for emp in employees:
        required_slots = int(emp.contracted_weekly_hours * SLOTS_PER_HOUR)
        existing_slots = int(existing_hours[emp.id] * SLOTS_PER_HOUR)
        needed_slots = required_slots - existing_slots
        
        if needed_slots <= 0:
            continue
        
        emp_shift_terms = []
        for key, var in shift_vars.items():
            if key[0] == emp.id:
                length = key[3]
                emp_shift_terms.append(length * var)
        
        if emp_shift_terms:
            total_new = model.NewIntVar(0, SLOTS_PER_DAY * 7, f"new_slots_{emp.id}")
            model.Add(total_new == sum(emp_shift_terms))
            
            # Shortfall = max(0, needed - total_new)
            shortfall = model.NewIntVar(0, needed_slots, f"shortfall_{emp.id}")
            model.AddMaxEquality(shortfall, [0, needed_slots - total_new])
            
            # Penalty per hour short (convert slots to hours)
            objective_terms.append((WEIGHT_UNMET_CONTRACTED_HOUR // SLOTS_PER_HOUR) * shortfall)
            hour_shortfall_vars[emp.id] = shortfall
    
    # 6. Overtime penalty (soft - small penalty for hours over contracted)
    overtime_vars = {}
    for emp in employees:
        contracted_slots = int(emp.contracted_weekly_hours * SLOTS_PER_HOUR)
        existing_slots = int(existing_hours[emp.id] * SLOTS_PER_HOUR)
        
        emp_shift_terms = []
        for key, var in shift_vars.items():
            if key[0] == emp.id:
                emp_shift_terms.append(key[3] * var)
        
        if emp_shift_terms:
            total_new = model.NewIntVar(0, SLOTS_PER_DAY * 7, f"total_new_{emp.id}")
            model.Add(total_new == sum(emp_shift_terms))
            
            overtime = model.NewIntVar(0, SLOTS_PER_DAY * 7, f"overtime_{emp.id}")
            model.AddMaxEquality(overtime, [0, total_new + existing_slots - contracted_slots])
            
            objective_terms.append((WEIGHT_OVERTIME_HOUR // SLOTS_PER_HOUR) * overtime)
            overtime_vars[emp.id] = overtime
    
    # 7. Department preference bonuses
    for key, var in shift_vars.items():
        emp_id, day, start, length, dept_id = key
        emp = emp_map[emp_id]
        
        if dept_id == emp.primary_department_id:
            objective_terms.append(WEIGHT_PRIMARY_DEPT * var)
        else:
            objective_terms.append(WEIGHT_NON_PRIMARY_DEPT * var)
    
    # 8. Preferred availability bonus
    for key, var in shift_vars.items():
        emp_id, day, start, length, _ = key
        pref = preferred[emp_id]
        
        # Check if all slots are preferred
        all_preferred = all(pref[day][s] for s in range(start, start + length))
        if all_preferred:
            objective_terms.append(WEIGHT_PREFERRED_AVAIL * var)
    
    # 9. Shift length preference bonus
    for key, var in shift_vars.items():
        length = key[3]
        bonus = _get_shift_length_bonus(length)
        objective_terms.append(bonus * var)
    
    # Set objective: maximize (since penalties are negative, this minimizes violations)
    if objective_terms:
        model.Maximize(sum(objective_terms))
    
    # ========== SOLVE ==========
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120.0
    status = solver.Solve(model)
    
    # ========== EXTRACT RESULTS ==========
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        shifts = []
        
        for key, var in shift_vars.items():
            if solver.Value(var) == 1:
                emp_id, day, start_slot, length, dept_id = key
                
                slot_date = context.week_start + timedelta(days=day)
                start_time = slot_to_time(start_slot)
                end_time = slot_to_time(start_slot + length)
                
                shifts.append(Shift(
                    employee_id=emp_id,
                    store_id=context.store_id,
                    department_id=dept_id,
                    start_datetime=datetime.combine(slot_date, start_time),
                    end_datetime=datetime.combine(slot_date, end_time),
                ))
        
        unmet_coverage = _check_unmet_coverage(shifts, context)
        unmet_roles = _check_unmet_roles(shifts, context)
        unmet_hours = _check_unmet_hours(shifts, context, existing_hours)
        
        warnings = []
        if status == cp_model.FEASIBLE:
            warnings.append("Solution may not be optimal (time limit reached)")
        
        return ScheduleResult(
            success=len(unmet_coverage) == 0 and len(unmet_roles) == 0 and len(unmet_hours) == 0,
            shifts=shifts,
            unmet_coverage=unmet_coverage,
            unmet_role_requirements=unmet_roles,
            unmet_contracted_hours=unmet_hours,
            warnings=warnings,
        )
    else:
        status_name = solver.StatusName(status)
        return ScheduleResult(
            success=False,
            shifts=[],
            warnings=[f"Solver status: {status_name} - no valid schedule found"],
        )


def _check_unmet_coverage(
    shifts: list[Shift],
    context: ScheduleContext,
) -> list[CoverageRequirement]:
    """Check which coverage requirements aren't fully met."""
    unmet = []
    all_shifts = shifts + context.existing_shifts
    
    for req in context.coverage_requirements:
        slot_date = context.week_start + timedelta(days=req.day_of_week)
        req_start = time_to_slot(req.start_time)
        req_end = time_to_slot(req.end_time)
        
        for slot in range(req_start, req_end):
            slot_time = slot_to_time(slot)
            slot_dt = datetime.combine(slot_date, slot_time)
            
            count = sum(
                1 for s in all_shifts
                if s.department_id == req.department_id
                and s.start_datetime <= slot_dt < s.end_datetime
            )
            
            if count < req.min_staff:
                unmet.append(req)
                break
    
    return unmet


def _check_unmet_roles(
    shifts: list[Shift],
    context: ScheduleContext,
) -> list[RoleRequirement]:
    """Check which role requirements aren't met."""
    unmet = []
    all_shifts = shifts + context.existing_shifts
    emp_map = {e.id: e for e in context.employees}
    
    for req in context.role_requirements:
        days = [req.day_of_week] if req.day_of_week is not None else list(range(7))
        req_start = time_to_slot(req.start_time)
        req_end = time_to_slot(req.end_time)
        
        is_met = True
        for day in days:
            if not is_met:
                break
            slot_date = context.week_start + timedelta(days=day)
            
            for slot in range(req_start, req_end):
                slot_time = slot_to_time(slot)
                slot_dt = datetime.combine(slot_date, slot_time)
                
                active_emps = [
                    emp_map[s.employee_id] for s in all_shifts
                    if s.start_datetime <= slot_dt < s.end_datetime
                    and s.employee_id in emp_map
                ]
                
                if req.requires_keyholder and not any(e.is_keyholder for e in active_emps):
                    is_met = False
                    break
                
                if req.requires_manager:
                    if sum(1 for e in active_emps if e.is_manager) < req.min_manager_count:
                        is_met = False
                        break
        
        if not is_met:
            unmet.append(req)
    
    return unmet


def _check_unmet_hours(
    shifts: list[Shift],
    context: ScheduleContext,
    existing_hours: dict[int, float],
) -> dict[int, float]:
    """Check which employees don't meet contracted hours."""
    shortfalls = {}
    
    for emp in context.employees:
        new_hours = sum(s.duration_hours for s in shifts if s.employee_id == emp.id)
        total = new_hours + existing_hours.get(emp.id, 0)
        shortfall = emp.contracted_weekly_hours - total
        
        if shortfall > 0.01:
            shortfalls[emp.id] = shortfall
    
    return shortfalls