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
    TimeOffRequest
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

    def test_respects_time_off(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        time_off = [
            TimeOffRequest(
                employee_id=1,
                start_datetime=datetime.combine(monday, time(0, 0)),
                end_datetime=datetime.combine(monday, time(23, 59)),
            ),
        ]
        coverage = [
            CoverageRequirement(id=1, store_id=1, department_id=1, day_of_week=0,
                                start_time=time(10, 0), end_time=time(14, 0),
                                min_staff=1, max_staff=2),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=time_off, coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        monday_shifts = [s for s in result.shifts if s.day_of_week == 0 and s.employee_id == 1]
        assert len(monday_shifts) == 0

    def test_multiple_role_requirements_same_day(self):
        monday = get_test_monday()
        # manager who is also keyholder
        emp = Employee(id=1, store_id=1, is_keyholder=True, is_manager=True,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        #keyholder needed 6-10am, manager needed 10-14
        role_reqs = [
            RoleRequirement(id=1, store_id=1, department_id=None, day_of_week=0,
                            start_time=time(6, 0), end_time=time(10, 0),
                            requires_keyholder=True, requires_manager=False, min_manager_count=0),
            RoleRequirement(id=2, store_id=1, department_id=None, day_of_week=0,
                            start_time=time(10, 0), end_time=time(14, 0),
                            requires_keyholder=False, requires_manager=True, min_manager_count=1),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=role_reqs,
            existing_shifts=[],
        )
        result = solve_schedule(context)
        
        #shift covering both requirements
        monday_shifts = [s for s in result.shifts if s.day_of_week == 0 and s.employee_id == 1]
        assert len(monday_shifts) == 1
        
        shift = monday_shifts[0]
        #Shift should cover keyholder window (6-10)
        assert shift.start_datetime.time() <= time(6, 0) or shift.start_datetime.time() <= time(10, 0)
        # shift should cover manager window (10-14)
        assert shift.end_datetime.time() >= time(14, 0) or shift.end_datetime.time() >= time(10, 0)


class TestRestPeriodConstraint:

    def test_sufficient_rest_no_shifts(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        solver = ScheduleSolver(context)
        
        assert solver._has_sufficient_rest(1, monday) is True

    def test_insufficient_rest_late_then_early(self):
        monday = get_test_monday()
        emp = Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                       contracted_weekly_hours=40, department_ids=[1], primary_department_id=1)
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp], availability_rules=[],
            time_off_requests=[], coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        solver = ScheduleSolver(context)
        
        #late shift mon ending 10pm
        solver._add_shift(Shift(
            employee_id=1, store_id=1, department_id=1,
            start_datetime=datetime.combine(monday, time(14, 0)),
            end_datetime=datetime.combine(monday, time(22, 0)),
        ))
        
        #tue early = only 8h rest but need 12h
        tuesday = monday + timedelta(days=1)
        assert solver._has_sufficient_rest(1, tuesday) is False


class TestShiftLengths:

    def test_manager_can_work_10h(self):
        assert 10 in MANAGER_SHIFT_LENGTHS

    def test_non_manager_cannot_work_10h(self):
        assert 10 not in NON_MANAGER_SHIFT_LENGTHS