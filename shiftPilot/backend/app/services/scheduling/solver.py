"""
Schedule solver using greedy seeding with backtracking.

Strategy:
1. Generate time slots that need coverage from requirements
2. Greedy pass: assign shifts to cover slots, prioritizing constrained slots
3. Backtrack when conflicts arise
4. Fill remaining contracted hours with additional shifts
"""

from datetime import datetime, date, time, timedelta
from typing import Optional
from collections import defaultdict

from .types import (
    Employee,
    Shift,
    CoverageRequirement,
    RoleRequirement,
    ScheduleContext,
    ScheduleResult,
    AvailabilityType,
)
from .availability import (
    can_employee_work_shift,
    get_available_employees_for_slot,
    get_availability_for_slot,
)
from .constraints import (
    check_coverage_at_time,
    check_role_requirement_at_time,
    calculate_employee_hours,
    get_shifts_covering_time,
)



SHIFT_LENGTHS = [8, 4, 6, 10] # Priority order
MANAGER_SHIFT_LENGTHS = [8, 4, 6, 10]  # Managers can do longer shifts
NON_MANAGER_SHIFT_LENGTHS = [8, 4, 6]  # Standard shift times
MIN_REST_HOURS = 12  # Minimum hours between shifts


class ScheduleSolver:
    """
    Constraint satisfaction solver for shift scheduling.
    """
    
    def __init__(self, context: ScheduleContext):
        self.context = context
        self.shifts: list[Shift] = list(context.existing_shifts)
        self.employee_hours: dict[int, float] = defaultdict(float)
        self.employee_days: dict[int, set[int]] = defaultdict(set)  # emp_id -> set of day_of_week worked
        
        # Initialize from existing shifts
        for shift in self.shifts:
            self.employee_hours[shift.employee_id] += shift.duration_hours
            self.employee_days[shift.employee_id].add(shift.day_of_week)
    
    def solve(self) -> ScheduleResult:
        """
        Main solving method.
        
        Returns:
            ScheduleResult with generated shifts and any unmet constraints
        """
        #1: Cover all coverage requirements
        self._cover_requirements()
        #2: Satisfy role requirements
        self._satisfy_role_requirements()
        #3: Fill contracted hours
        self._fill_contracted_hours()
        #4: Retry coverage gaps (some employees may now be available)
        self._retry_coverage_gaps()
        #5: Result
        return self._build_result()
    
    def _retry_coverage_gaps(self):
        """Retry filling any remaining coverage gaps after contracted hours filled."""
        sorted_reqs = self._sort_requirements_by_constraint()
        for req in sorted_reqs:
            self._cover_single_requirement(req)
    
    def _cover_requirements(self):
        """1: Generate shifts to meet coverage requirements."""
        
        # Sort requirements by most constrained first (fewer available employees)
        sorted_reqs = self._sort_requirements_by_constraint()
        
        # First pass
        for req in sorted_reqs:
            self._cover_single_requirement(req)
        
        # Second pass - retry any gaps (employees may now be available on different days)
        for req in sorted_reqs:
            self._cover_single_requirement(req)
    
    def _sort_requirements_by_constraint(self) -> list[CoverageRequirement]:
        """Sort coverage requirements - hardest to fill first."""
        
        def constraint_score(req: CoverageRequirement) -> tuple[float, int]:
            slot_date = self.context.week_start + timedelta(days=req.day_of_week)
            start_dt = datetime.combine(slot_date, req.start_time)
            end_dt = datetime.combine(slot_date, req.end_time)
            
            available = get_available_employees_for_slot(
                self.context.employees,
                start_dt,
                end_dt,
                req.department_id,
                self.context.availability_rules,
                self.context.time_off_requests,
                self.shifts,
            )
            # Ratio of available employees to required staff (lower = harder)
            ratio = len(available) / max(req.min_staff, 1)
            return (ratio, -req.min_staff)
        
        return sorted(self.context.coverage_requirements, key=constraint_score)
    
    def _cover_single_requirement(self, req: CoverageRequirement):
        """Attempt to cover a single coverage requirement."""
        
        slot_date = self.context.week_start + timedelta(days=req.day_of_week)
        window_start = datetime.combine(slot_date, req.start_time)
        window_end = datetime.combine(slot_date, req.end_time)
        
        # Sample through the window to find gaps
        interval = timedelta(minutes=30)
        current = window_start
        
        while current < window_end:
            is_met, current_count, required = check_coverage_at_time(
                self.shifts, self.context.employees, req, current
            )
            
            if not is_met:
                # Need to add staff at this time
                needed = required - current_count
                for _ in range(needed):
                    shift = self._find_best_shift_for_time(
                        current, req.department_id, window_start, window_end
                    )
                    if shift:
                        self._add_shift(shift)
            
            current += interval
    
    def _find_best_shift_for_time(
        self,
        target_time: datetime,
        department_id: int,
        window_start: datetime,
        window_end: datetime
    ) -> Optional[Shift]:
        """
        Find the best shift to cover a target time within a coverage window.
        Scores all valid candidates and picks the best.
        """
        day_of_week = target_time.weekday()
        target_date = target_time.date()
        
        # employees who can work this department
        candidates = [
            e for e in self.context.employees
            if department_id in e.department_ids
        ]
        
        # Score all valid (employee, shift) combinations
        scored_options: list[tuple[float, Shift, Employee]] = []
        
        for emp in candidates:
            # Skip if already working this day
            if day_of_week in self.employee_days[emp.id]:
                continue
            
            # Check rest constraint
            if not self._has_sufficient_rest(emp.id, target_date):
                continue
            
            # Get allowed shift lengths
            allowed_lengths = MANAGER_SHIFT_LENGTHS if emp.is_manager else NON_MANAGER_SHIFT_LENGTHS
            
            for length in allowed_lengths:
                shift = self._find_valid_shift_time(
                    emp, department_id, target_date, length, window_start, window_end, target_time
                )
                
                if shift:
                    score = self._score_shift(shift, emp, department_id)
                    scored_options.append((score, shift, emp))
        
        if not scored_options:
            return None
        
        # Sort by score descending, pick best
        scored_options.sort(key=lambda x: -x[0])
        return scored_options[0][1]
    
    def _find_valid_shift_time(
        self,
        employee: Employee,
        department_id: int,
        target_date: date,
        length_hours: int,
        window_start: datetime,
        window_end: datetime,
        must_cover: datetime
    ) -> Optional[Shift]:
        """
        Find a valid shift start time for an employee on a given day.
        The shift must cover the must_cover time and overlap with the window.
        """
        
        length = timedelta(hours=length_hours)
        
        # Shift must start at or before must_cover and end after must_cover
        earliest_start = must_cover - length + timedelta(minutes=30)
        latest_start = must_cover
        
        ######## TO DO: ADD CUSTOMISABLE WORKING HOURS PER STORE ########
        # Constrain to set working hours (6am-10pm)
        day_start = datetime.combine(target_date, time(6, 0))
        day_end = datetime.combine(target_date, time(22, 0))
        
        earliest_start = max(earliest_start, day_start)
        latest_start = min(latest_start, day_end - length)
        
        if earliest_start > latest_start:
            return None
        
        # Try start times in 30-min increments, prefer times that align with the window
        best_start = None
        best_overlap = timedelta(0)
        
        current_start = earliest_start
        while current_start <= latest_start:
            shift_end = current_start + length
            
            # Check if employee can work this shift
            can_work, _ = can_employee_work_shift(
                employee,
                current_start,
                shift_end,
                department_id,
                self.context.availability_rules,
                self.context.time_off_requests,
                self.shifts,
            )
            
            if can_work:
                # Calculate overlap with coverage window
                overlap_start = max(current_start, window_start)
                overlap_end = min(shift_end, window_end)
                overlap = overlap_end - overlap_start
                
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_start = current_start
            
            current_start += timedelta(minutes=30)
        
        if best_start:
            return Shift(
                employee_id=employee.id,
                store_id=self.context.store_id,
                department_id=department_id,
                start_datetime=best_start,
                end_datetime=best_start + length,
            )
        
        return None
    
    def _has_sufficient_rest(self, employee_id: int, target_date: date) -> bool:
        """Check if employee has 12h rest before/after working on target_date."""
        
        min_rest = timedelta(hours=MIN_REST_HOURS)
        
        for shift in self.shifts:
            if shift.employee_id != employee_id:
                continue
            
            shift_date = shift.start_datetime.date()
            
            # Check day before
            if shift_date == target_date - timedelta(days=1):
                # Shift ends on previous day, need 12h before midnight + time into target day
                day_start = datetime.combine(target_date, time(6, 0))  # Earliest possible start
                if day_start - shift.end_datetime < min_rest:
                    return False
            
            # Check day after
            if shift_date == target_date + timedelta(days=1):
                # Would need 12h rest after target day shift ends
                day_end = datetime.combine(target_date, time(22, 0))  # Latest reasonable end
                if shift.start_datetime - day_end < min_rest:
                    return False
        
        return True
    
    def _score_shift(self, shift: Shift, employee: Employee, department_id: int) -> float:
        ###### TO DO: ENHANCE SCORING WITH MORE FACTORS ######
        """
        Score a potential shift assignment. Higher = better.
        
        Factors:
        - Preference for primary department
        - Preference for PREFERRED availability
        - Preference for 8h shifts
        - Penalty for overtime (exceeding contracted hours)
        - Preference for employees with hours still needed
        - Bonus for departments with higher min_staff requirements
        """
        score = 0.0
        
        # Department staffing need bonus - prioritize depts that need more people
        dept_min_staff = max(
            (req.min_staff for req in self.context.coverage_requirements 
             if req.department_id == department_id),
            default=1
        )
        score += dept_min_staff * 5  # +10 for 2-staff depts, +5 for 1-staff
        
        # Primary department bonus
        if department_id == employee.primary_department_id:
            score += 25
        else:
            score -= 15  # Penalty for non-primary dept
        
        # Availability preference bonus
        avail = get_availability_for_slot(
            employee.id,
            shift.day_of_week,
            shift.start_datetime.time(),
            shift.end_datetime.time(),
            self.context.availability_rules
        )
        if avail == AvailabilityType.PREFERRED:
            score += 15
        elif avail == AvailabilityType.AVAILABLE:
            score += 5
        
        # Shift length scoring (prefer 8h)
        length = shift.duration_hours
        if length == 8:
            score += 10
        elif length == 4:
            score += 7
        elif length == 6:
            score += 5
        elif length == 10:
            score += 3
        
        # Hours needed - prefer assigning to those who need hours
        current_hours = self.employee_hours[employee.id]
        needed = employee.contracted_weekly_hours - current_hours
        
        if needed > 0:
            # Bonus for filling needed hours
            fills = min(shift.duration_hours, needed)
            score += fills * 2
        else:
            # Penalty for overtime
            overtime = shift.duration_hours
            score -= overtime * 3
        
        # Penalty for working too many days
        days_worked = len(self.employee_days[employee.id])
        if days_worked >= 5:
            score -= 20
        elif days_worked >= 4:
            score -= 5
        
        return score
    
    def _add_shift(self, shift: Shift):
        """Add a shift to the schedule and update tracking."""
        self.shifts.append(shift)
        self.employee_hours[shift.employee_id] += shift.duration_hours
        self.employee_days[shift.employee_id].add(shift.day_of_week)
    
    def _satisfy_role_requirements(self):
        """2: Ensure keyholder/manager requirements are met."""
        
        for req in self.context.role_requirements:
            self._satisfy_single_role_requirement(req)
    
    def _satisfy_single_role_requirement(self, req: RoleRequirement):
        """Ensure a role requirement is satisfied."""
        
        # Determine which days this applies to
        days = [req.day_of_week] if req.day_of_week is not None else list(range(7))
        
        for day in days:
            slot_date = self.context.week_start + timedelta(days=day)
            window_start = datetime.combine(slot_date, req.start_time)
            window_end = datetime.combine(slot_date, req.end_time)
            
            # Check at intervals
            interval = timedelta(minutes=30)
            current = window_start
            
            while current < window_end:
                is_met, reason = check_role_requirement_at_time(
                    self.shifts, self.context.employees, req, current
                )
                
                if not is_met:
                    # Need to add a keyholder/manager
                    shift = self._find_role_shift(req, current, window_start, window_end, day)
                    if shift:
                        self._add_shift(shift)
                
                current += interval
    
    def _find_role_shift(
        self,
        req: RoleRequirement,
        target_time: datetime,
        window_start: datetime,
        window_end: datetime,
        day_of_week: int
    ) -> Optional[Shift]:
        """Find a shift that satisfies a role requirement."""
        
        target_date = target_time.date()
        
        # Get candidates with required role
        candidates = []
        for emp in self.context.employees:
            if req.requires_keyholder and not emp.is_keyholder:
                continue
            if req.requires_manager and not emp.is_manager:
                continue
            candidates.append(emp)
        
        # Score all valid options
        scored_options: list[tuple[float, Shift, Employee]] = []
        
        for emp in candidates:
            # Skip if already working this day
            if day_of_week in self.employee_days[emp.id]:
                # Check if existing shift covers the time
                existing_covers = any(
                    s.employee_id == emp.id and 
                    s.start_datetime <= target_time < s.end_datetime
                    for s in self.shifts
                )
                if existing_covers:
                    continue  # Already covering
                continue  # Working but not covering this time
            
            if not self._has_sufficient_rest(emp.id, target_date):
                continue
            
            # Determine department - use primary or any they're assigned to
            dept_id = emp.primary_department_id or (emp.department_ids[0] if emp.department_ids else None)
            if req.department_id:
                if req.department_id not in emp.department_ids:
                    continue
                dept_id = req.department_id
            
            if not dept_id:
                continue
            
            allowed_lengths = MANAGER_SHIFT_LENGTHS if emp.is_manager else NON_MANAGER_SHIFT_LENGTHS
            
            for length in allowed_lengths:
                shift = self._find_valid_shift_time(
                    emp, dept_id, target_date, length, window_start, window_end, target_time
                )
                
                if shift:
                    score = self._score_shift(shift, emp, dept_id)
                    score += 20  # Bonus for role match
                    scored_options.append((score, shift, emp))
        
        if not scored_options:
            return None
        
        # Sort by score descending, pick best
        scored_options.sort(key=lambda x: -x[0])
        return scored_options[0][1]
    
    def _fill_contracted_hours(self):
        """3: Assign additional shifts to meet contracted hours."""
        
        # Multiple passes to ensure we fill hours
        for _ in range(3):
            employees_needing_hours = [
                (emp, emp.contracted_weekly_hours - self.employee_hours[emp.id])
                for emp in self.context.employees
                if self.employee_hours[emp.id] < emp.contracted_weekly_hours
            ]
            
            if not employees_needing_hours:
                break
                
            # Sort employees by hours (most needed first)
            employees_needing_hours.sort(key=lambda x: -x[1])
            
            for emp, needed in employees_needing_hours:
                self._fill_employee_hours(emp, needed)
    
    def _fill_employee_hours(self, employee: Employee, needed: float):
        """Try to fill an employee's contracted hours with additional shifts."""
        
        allowed_lengths = MANAGER_SHIFT_LENGTHS if employee.is_manager else NON_MANAGER_SHIFT_LENGTHS
        
        # Try to add shifts on days they're not working
        for day in range(7):
            if needed <= 0:
                break
            
            if day in self.employee_days[employee.id]:
                continue
            
            target_date = self.context.week_start + timedelta(days=day)
            
            if not self._has_sufficient_rest(employee.id, target_date):
                continue
            
            # Try each shift length, preferring longer shifts to fill hours faster
            for length in sorted(allowed_lengths, reverse=True):
                shift = self._find_open_shift(employee, target_date, length)
                if shift:
                    self._add_shift(shift)
                    needed -= shift.duration_hours
                    break
    
    def _find_open_shift(
        self, 
        employee: Employee, 
        target_date: date, 
        length_hours: int
    ) -> Optional[Shift]:
        """Find an open shift slot for an employee on a given day."""
        
        length = timedelta(hours=length_hours)
        
        # Try primary department first, then others
        departments_to_try = []
        if employee.primary_department_id:
            departments_to_try.append(employee.primary_department_id)
        for dept_id in employee.department_ids:
            if dept_id not in departments_to_try:
                departments_to_try.append(dept_id)
        
        for dept_id in departments_to_try:
            # Try different start times
            for hour in range(6, 19):  # 6am to 6pm starts
                start = datetime.combine(target_date, time(hour, 0))
                end = start + length
                
                can_work, _ = can_employee_work_shift(
                    employee,
                    start,
                    end,
                    dept_id,
                    self.context.availability_rules,
                    self.context.time_off_requests,
                    self.shifts,
                )
                
                if can_work:
                    return Shift(
                        employee_id=employee.id,
                        store_id=self.context.store_id,
                        department_id=dept_id,
                        start_datetime=start,
                        end_datetime=end,
                    )
        
        return None
    
    def _build_result(self) -> ScheduleResult:
        """4: Build the final result with any unmet constraints."""
        
        from .constraints import validate_schedule
        
        validation = validate_schedule(self.context, self.shifts)
        
        # show unmet requirements
        unmet_coverage = [req for req, gaps in validation['coverage_gaps']]
        unmet_roles = [req for req, gaps in validation['role_gaps']]
        
        warnings = []
        
        if unmet_coverage:
            warnings.append(f"{len(unmet_coverage)} coverage requirements not fully met")
        
        if unmet_roles:
            warnings.append(f"{len(unmet_roles)} role requirements not fully met")
        
        if validation['hour_shortfalls']:
            count = len(validation['hour_shortfalls'])
            warnings.append(f"{count} employees under contracted hours")
        
        # exclude existing shifts - only return NEW shifts created by solver
        existing_ids = {
            (s.employee_id, s.start_datetime, s.end_datetime) 
            for s in self.context.existing_shifts
        }
        new_shifts = [
            s for s in self.shifts 
            if (s.employee_id, s.start_datetime, s.end_datetime) not in existing_ids
        ]
        
        return ScheduleResult(
            success=validation['valid'],
            shifts=new_shifts,
            unmet_coverage=unmet_coverage,
            unmet_role_requirements=unmet_roles,
            unmet_contracted_hours=validation['hour_shortfalls'],
            warnings=warnings,
        )


def solve_schedule(context: ScheduleContext) -> ScheduleResult:
    """
    Main entry point for schedule generation.
    
    Args:
        context: ScheduleContext with all required data
        
    Returns:
        ScheduleResult with generated shifts
    """
    solver = ScheduleSolver(context)
    return solver.solve()