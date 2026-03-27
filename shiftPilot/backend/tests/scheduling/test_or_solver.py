"""
Unit tests for OR-Tools based schedule solver.
"""
import pytest
from datetime import time, datetime, timedelta, date

from app.services.scheduling.types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    CoverageRequirement,
    RoleRequirement,
    Shift,
    ScheduleContext,
    TimeOffRequest,
)
from app.services.scheduling.or_solver import (
    solve_schedule,
    slot_to_time,
    time_to_slot,
    get_valid_shift_lengths,
    SLOTS_PER_HOUR,
    MIN_SHIFT_HOURS,
    MAX_REGULAR_HOURS,
    MAX_MANAGER_HOURS,
)


def get_test_monday() -> date:
    """Get a consistent Monday for testing."""
    today = date.today()
    days_ahead = 7 - today.weekday()
    return today + timedelta(days=days_ahead)


class TestSlotConversions:

    def test_slot_0_is_6am(self):
        assert slot_to_time(0) == time(6, 0)

    def test_slot_2_is_7am(self):
        assert slot_to_time(2) == time(7, 0)

    def test_slot_8_is_10am(self):
        assert slot_to_time(8) == time(10, 0)

    def test_time_to_slot_6am(self):
        assert time_to_slot(time(6, 0)) == 0

    def test_time_to_slot_10am(self):
        assert time_to_slot(time(10, 0)) == 8

    def test_time_to_slot_630am(self):
        assert time_to_slot(time(6, 30)) == 1

    def test_roundtrip_conversion(self):
        for slot in range(0, 32, 2):
            t = slot_to_time(slot)
            assert time_to_slot(t) == slot


class TestShiftLengths:

    def test_manager_min_4h(self):
        lengths = get_valid_shift_lengths(is_manager=True)
        assert min(lengths) == MIN_SHIFT_HOURS * SLOTS_PER_HOUR

    def test_manager_max_12h(self):
        lengths = get_valid_shift_lengths(is_manager=True)
        assert max(lengths) == MAX_MANAGER_HOURS * SLOTS_PER_HOUR

    def test_regular_min_4h(self):
        lengths = get_valid_shift_lengths(is_manager=False)
        assert min(lengths) == MIN_SHIFT_HOURS * SLOTS_PER_HOUR

    def test_regular_max_9h(self):
        lengths = get_valid_shift_lengths(is_manager=False)
        assert max(lengths) == MAX_REGULAR_HOURS * SLOTS_PER_HOUR

    def test_lengths_are_hourly_increments(self):
        for is_mgr in [True, False]:
            lengths = get_valid_shift_lengths(is_mgr)
            for length in lengths:
                assert length % SLOTS_PER_HOUR == 0


class TestSolverBasics:

    def test_empty_requirements_succeeds(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=0, department_ids=[1], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        assert result.success is True
        assert len(result.shifts) == 0

    def test_generates_shifts_for_coverage(self):
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
            Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
        ]
        coverage = [
            CoverageRequirement(
                id=1, store_id=1, department_id=1, day_of_week=0,
                start_time=time(10, 0), end_time=time(14, 0),
                min_staff=2, max_staff=3
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees,
            availability_rules=[], time_off_requests=[],
            coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        monday_shifts = [s for s in result.shifts if s.day_of_week == 0]
        assert len(monday_shifts) >= 2

    def test_one_shift_per_day_per_employee(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=40, department_ids=[1], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        from collections import Counter
        day_counts = Counter((s.employee_id, s.day_of_week) for s in result.shifts)
        for (emp_id, day), count in day_counts.items():
            assert count == 1, f"Employee {emp_id} has {count} shifts on day {day}"

    def test_all_shifts_valid_length(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=32, department_ids=[1], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        for shift in result.shifts:
            assert shift.duration_hours >= MIN_SHIFT_HOURS
            assert shift.duration_hours <= MAX_REGULAR_HOURS


class TestAvailabilityConstraints:

    def test_respects_unavailability(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=8, department_ids=[1], primary_department_id=1
        )
        rules = [
            AvailabilityRule(
                employee_id=1, day_of_week=0,
                rule_type=AvailabilityType.UNAVAILABLE,
                start_time=None, end_time=None
            ),
        ]
        coverage = [
            CoverageRequirement(
                id=1, store_id=1, department_id=1, day_of_week=0,
                start_time=time(10, 0), end_time=time(14, 0),
                min_staff=1, max_staff=2
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=rules, time_off_requests=[],
            coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        monday_shifts = [s for s in result.shifts if s.day_of_week == 0 and s.employee_id == 1]
        assert len(monday_shifts) == 0

    def test_respects_time_off(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=8, department_ids=[1], primary_department_id=1
        )
        time_off = [
            TimeOffRequest(
                employee_id=1,
                start_datetime=datetime.combine(monday, time(0, 0)),
                end_datetime=datetime.combine(monday + timedelta(days=1), time(0, 0)),
            ),
        ]
        coverage = [
            CoverageRequirement(
                id=1, store_id=1, department_id=1, day_of_week=0,
                start_time=time(10, 0), end_time=time(14, 0),
                min_staff=1, max_staff=2
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=time_off,
            coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        monday_shifts = [s for s in result.shifts if s.day_of_week == 0 and s.employee_id == 1]
        assert len(monday_shifts) == 0

    def test_respects_partial_availability(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=4, department_ids=[1], primary_department_id=1
        )
        rules = [
            AvailabilityRule(
                employee_id=1, day_of_week=0,
                rule_type=AvailabilityType.AVAILABLE,
                start_time=time(8, 0), end_time=time(12, 0)
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=rules, time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        for shift in result.shifts:
            if shift.employee_id == 1 and shift.day_of_week == 0:
                assert shift.start_datetime.time() >= time(8, 0)
                assert shift.end_datetime.time() <= time(12, 0)


class TestRoleRequirements:

    def test_schedules_keyholder_when_required(self):
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=True, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
            Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
        ]
        role_req = RoleRequirement(
            id=1, store_id=1, department_id=None, day_of_week=0,
            start_time=time(8, 0), end_time=time(10, 0),
            requires_keyholder=True, requires_manager=False, min_manager_count=0,
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees,
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[role_req],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Role requirement should be met
        assert len(result.unmet_role_requirements) == 0

    def test_reports_impossible_role_requirement(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=8, department_ids=[1], primary_department_id=1
        )
        role_req = RoleRequirement(
            id=1, store_id=1, department_id=None, day_of_week=0,
            start_time=time(8, 0), end_time=time(10, 0),
            requires_keyholder=True, requires_manager=False, min_manager_count=0,
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[role_req],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Should report unmet since no keyholders available
        assert len(result.unmet_role_requirements) > 0


class TestCoverageRequirements:

    def test_meets_min_staff_coverage(self):
        monday = get_test_monday()
        employees = [
            Employee(id=i, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1)
            for i in range(1, 4)
        ]
        coverage = CoverageRequirement(
            id=1, store_id=1, department_id=1, day_of_week=0,
            start_time=time(10, 0), end_time=time(14, 0),
            min_staff=3, max_staff=4
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees,
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[coverage], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Coverage should be met
        assert len(result.unmet_coverage) == 0

    def test_reports_impossible_coverage(self):
        monday = get_test_monday()
        coverage = CoverageRequirement(
            id=1, store_id=1, department_id=1, day_of_week=0,
            start_time=time(10, 0), end_time=time(14, 0),
            min_staff=5, max_staff=10
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[coverage], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        assert len(result.unmet_coverage) > 0


class TestRestPeriodConstraint:

    def test_enforces_12h_rest_between_days(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=16, department_ids=[1], primary_department_id=1
        )
        # Coverage forcing late Monday and early Tuesday
        coverage = [
            CoverageRequirement(
                id=1, store_id=1, department_id=1, day_of_week=0,
                start_time=time(18, 0), end_time=time(22, 0),
                min_staff=1, max_staff=2
            ),
            CoverageRequirement(
                id=2, store_id=1, department_id=1, day_of_week=1,
                start_time=time(6, 0), end_time=time(10, 0),
                min_staff=1, max_staff=2
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        mon_shift = next((s for s in result.shifts if s.day_of_week == 0), None)
        tue_shift = next((s for s in result.shifts if s.day_of_week == 1), None)

        if mon_shift and tue_shift:
            end_monday = mon_shift.end_datetime
            start_tuesday = tue_shift.start_datetime
            rest_hours = (start_tuesday - end_monday).total_seconds() / 3600
            assert rest_hours >= 12, f"Only {rest_hours}h rest between shifts"


class TestContractedHours:

    def test_prioritizes_contracted_hours(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=32, department_ids=[1], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        total_hours = sum(s.duration_hours for s in result.shifts if s.employee_id == 1)
        # Should meet or be close to contracted hours
        assert total_hours >= 28  # Allow some slack

    def test_accounts_for_existing_shifts(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=16, department_ids=[1], primary_department_id=1
        )
        existing = [
            Shift(
                employee_id=1, store_id=1, department_id=1,
                start_datetime=datetime.combine(monday, time(9, 0)),
                end_datetime=datetime.combine(monday, time(17, 0)),
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=existing,
        )
        result = solve_schedule(context)

        new_hours = sum(s.duration_hours for s in result.shifts if s.employee_id == 1)
        total_hours = new_hours + 8
        assert total_hours >= 14  # Allow some slack


class TestExistingShifts:

    def test_does_not_double_book_existing_shift_day(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=16, department_ids=[1], primary_department_id=1
        )
        existing = [
            Shift(
                employee_id=1, store_id=1, department_id=1,
                start_datetime=datetime.combine(monday, time(9, 0)),
                end_datetime=datetime.combine(monday, time(17, 0)),
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=existing,
        )
        result = solve_schedule(context)

        monday_new_shifts = [s for s in result.shifts if s.employee_id == 1 and s.day_of_week == 0]
        assert len(monday_new_shifts) == 0


class TestDepartmentAssignment:

    def test_only_assigns_to_valid_departments(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=8, department_ids=[1, 2], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        for shift in result.shifts:
            assert shift.department_id in emp.department_ids

    def test_prefers_primary_department(self):
        monday = get_test_monday()
        emp = Employee(
            id=1, store_id=1, is_keyholder=False, is_manager=False,
            contracted_weekly_hours=8, department_ids=[1, 2], primary_department_id=1
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=[emp],
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Most shifts should be in primary department
        primary_shifts = [s for s in result.shifts if s.department_id == 1]
        assert len(primary_shifts) >= len(result.shifts) // 2


class TestSoftConstraintPriorities:

    def test_coverage_prioritized_over_contracted_hours(self):
        """Coverage should be met even if it means some employees are short hours."""
        monday = get_test_monday()
        # 2 employees, but coverage needs both
        employees = [
            Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
            Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
        ]
        coverage = [
            CoverageRequirement(
                id=1, store_id=1, department_id=1, day_of_week=0,
                start_time=time(10, 0), end_time=time(18, 0),
                min_staff=2, max_staff=3
            ),
        ]
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees,
            availability_rules=[], time_off_requests=[],
            coverage_requirements=coverage, role_requirements=[],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Coverage should be met
        assert len(result.unmet_coverage) == 0

    def test_role_requirement_prioritized(self):
        """Role requirements should be met even if suboptimal for hours."""
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=True, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
            Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
        ]
        role_req = RoleRequirement(
            id=1, store_id=1, department_id=None, day_of_week=0,
            start_time=time(7, 0), end_time=time(10, 0),
            requires_keyholder=True, requires_manager=False, min_manager_count=0,
        )
        context = ScheduleContext(
            store_id=1, week_start=monday, employees=employees,
            availability_rules=[], time_off_requests=[],
            coverage_requirements=[], role_requirements=[role_req],
            existing_shifts=[],
        )
        result = solve_schedule(context)

        # Role requirement should be met
        assert len(result.unmet_role_requirements) == 0