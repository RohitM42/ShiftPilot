import pytest
from datetime import time, datetime, timedelta

from app.services.scheduling.types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    CoverageRequirement,
    RoleRequirement,
    Shift,
    ScheduleContext,
)
from app.services.scheduling.solver import (
    ScheduleSolver,
    solve_schedule,
    MANAGER_SHIFT_LENGTHS,
    NON_MANAGER_SHIFT_LENGTHS,
)

from conftest import get_test_monday


class TestScheduleSolverInit:

    def test_initializes_empty(self):
        monday = get_test_monday()
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        solver = ScheduleSolver(context)
        
        assert len(solver.shifts) == 0
        assert len(solver.employee_hours) == 0

    def test_tracks_existing_shifts(self):
        monday = get_test_monday()
        existing = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=existing,
        )
        solver = ScheduleSolver(context)
        
        assert len(solver.shifts) == 1
        assert solver.employee_hours[1] == 8.0
        assert 0 in solver.employee_days[1]


class TestSolverIntegration:

    def test_solve_empty_requirements(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=0, department_ids=[1], primary_department_id=1)
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        assert result.success is True
        assert len(result.shifts) == 0

    def test_generates_shifts_for_coverage(self):
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
            Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
        ]
        coverage = [
            CoverageRequirement(id=1, store_id=1, department_id=1, day_of_week=0,
                                start_time=time(10, 0), end_time=time(14, 0),
                                min_staff=2, max_staff=3),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees, availability_rules=[],
            time_off_requests=[], coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        monday_shifts = [s for s in result.shifts if s.day_of_week == 0]
        assert len(monday_shifts) >= 2

    def test_respects_unavailability(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        rules = [
            AvailabilityRule(employee_id=1, day_of_week=0,
                             rule_type=AvailabilityType.UNAVAILABLE,
                             start_time=None, end_time=None),
        ]
        coverage = [
            CoverageRequirement(id=1, store_id=1, department_id=1, day_of_week=0,
                                start_time=time(10, 0), end_time=time(14, 0),
                                min_staff=1, max_staff=2),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=rules,
            time_off_requests=[], coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        monday_shifts = [s for s in result.shifts if s.day_of_week == 0 and s.employee_id == 1]
        assert len(monday_shifts) == 0

    def test_one_shift_per_day_per_employee(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        from collections import Counter
        day_counts = Counter((s.employee_id, s.day_of_week) for s in result.shifts)
        for (emp_id, day), count in day_counts.items():
            assert count == 1, f"Employee {emp_id} has {count} shifts on day {day}"

    def test_reports_impossible_coverage(self):
        monday = get_test_monday()
        coverage = [
            CoverageRequirement(id=1, store_id=1, department_id=1, day_of_week=0,
                                start_time=time(10, 0), end_time=time(14, 0),
                                min_staff=5, max_staff=10),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[], availability_rules=[],
            time_off_requests=[], coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        assert result.success is False
        assert len(result.unmet_coverage) > 0

    def test_reports_impossible_role_requirement(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        role_req = RoleRequirement(
            id=1, store_id=1, department_id=None, day_of_week=0,
            start_time=time(8, 0), end_time=time(10, 0),
            requires_keyholder=True, requires_manager=False, min_manager_count=0,
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[role_req],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        assert result.success is False
        assert len(result.unmet_role_requirements) > 0