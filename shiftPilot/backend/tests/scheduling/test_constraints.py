import pytest
from datetime import time, datetime, timedelta

from app.services.scheduling.types import (
    Employee,
    Shift,
)
from app.services.scheduling.constraints import (
    get_shifts_covering_time,
    check_coverage_at_time,
    check_coverage_for_window,
    check_role_requirement_at_time,
    calculate_employee_hours,
    check_contracted_hours,
    validate_schedule,
)

from conftest import get_test_monday


class TestGetShiftsCoveringTime:

    def test_finds_active_shifts(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(8, 0)),
                  end_datetime=datetime.combine(monday, time(16, 0))),
            Shift(employee_id=2, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(12, 0)),
                  end_datetime=datetime.combine(monday, time(20, 0))),
        ]
        check_time = datetime.combine(monday, time(14, 0))
        
        covering = get_shifts_covering_time(shifts, check_time)
        assert len(covering) == 2

    def test_excludes_ended_shifts(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(8, 0)),
                  end_datetime=datetime.combine(monday, time(12, 0))),
        ]
        check_time = datetime.combine(monday, time(14, 0))
        
        covering = get_shifts_covering_time(shifts, check_time)
        assert len(covering) == 0

    def test_filters_by_department(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(8, 0)),
                  end_datetime=datetime.combine(monday, time(16, 0))),
            Shift(employee_id=2, store_id=1, department_id=2,
                  start_datetime=datetime.combine(monday, time(8, 0)),
                  end_datetime=datetime.combine(monday, time(16, 0))),
        ]
        check_time = datetime.combine(monday, time(10, 0))
        
        covering = get_shifts_covering_time(shifts, check_time, department_id=1)
        assert len(covering) == 1
        assert covering[0].department_id == 1


class TestCheckCoverageAtTime:

    def test_coverage_met(self, coverage_req, three_employees):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
            Shift(employee_id=2, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(10, 0)),
                  end_datetime=datetime.combine(monday, time(18, 0))),
        ]
        check_time = datetime.combine(monday, time(12, 0))
        
        is_met, current, required = check_coverage_at_time(
            shifts, three_employees, coverage_req, check_time
        )
        assert is_met is True
        assert current == 2

    def test_coverage_not_met(self, coverage_req, three_employees):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        check_time = datetime.combine(monday, time(12, 0))
        
        is_met, current, required = check_coverage_at_time(
            shifts, three_employees, coverage_req, check_time
        )
        assert is_met is False
        assert current == 1


class TestCheckRoleRequirementAtTime:

    def test_keyholder_present(self, keyholder_req, employees_with_roles):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=2, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(6, 0)),
                  end_datetime=datetime.combine(monday, time(14, 0))),
        ]
        check_time = datetime.combine(monday, time(8, 0))
        
        is_met, reason = check_role_requirement_at_time(
            shifts, employees_with_roles, keyholder_req, check_time
        )
        assert is_met is True

    def test_keyholder_missing(self, keyholder_req, employees_with_roles):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=3, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(6, 0)),
                  end_datetime=datetime.combine(monday, time(14, 0))),
        ]
        check_time = datetime.combine(monday, time(8, 0))
        
        is_met, reason = check_role_requirement_at_time(
            shifts, employees_with_roles, keyholder_req, check_time
        )
        assert is_met is False

    def test_manager_present(self, manager_req, employees_with_roles):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        check_time = datetime.combine(monday, time(12, 0))
        
        is_met, reason = check_role_requirement_at_time(
            shifts, employees_with_roles, manager_req, check_time
        )
        assert is_met is True

    def test_manager_missing(self, manager_req, employees_with_roles):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=2, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        check_time = datetime.combine(monday, time(12, 0))
        
        is_met, reason = check_role_requirement_at_time(
            shifts, employees_with_roles, manager_req, check_time
        )
        assert is_met is False


class TestCalculateEmployeeHours:

    def test_single_shift(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        assert calculate_employee_hours(shifts, 1) == 8.0

    def test_multiple_shifts(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday + timedelta(days=1), time(9, 0)),
                  end_datetime=datetime.combine(monday + timedelta(days=1), time(13, 0))),
        ]
        assert calculate_employee_hours(shifts, 1) == 12.0

    def test_only_counts_own_shifts(self):
        monday = get_test_monday()
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
            Shift(employee_id=2, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        assert calculate_employee_hours(shifts, 1) == 8.0


class TestCheckContractedHours:

    def test_no_shortfall(self):
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=8, department_ids=[1], primary_department_id=1),
        ]
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        shortfalls = check_contracted_hours(shifts, employees)
        assert len(shortfalls) == 0

    def test_detects_shortfall(self):
        monday = get_test_monday()
        employees = [
            Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                     contracted_weekly_hours=32, department_ids=[1], primary_department_id=1),
        ]
        shifts = [
            Shift(employee_id=1, store_id=1, department_id=1,
                  start_datetime=datetime.combine(monday, time(9, 0)),
                  end_datetime=datetime.combine(monday, time(17, 0))),
        ]
        shortfalls = check_contracted_hours(shifts, employees)
        assert 1 in shortfalls
        assert shortfalls[1] == 24.0