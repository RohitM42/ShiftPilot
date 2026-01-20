import pytest
from datetime import date, time, datetime, timedelta


from app.services.scheduling.types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    TimeOffRequest,
    Shift,
)
from app.services.scheduling.availability import (
    times_overlap,
    is_employee_on_time_off,
    get_availability_for_slot,
    can_employee_work_shift,
    get_available_employees_for_slot,
)

from conftest import get_test_monday


class TestTimesOverlap:
    def test_no_overlap(self):
        assert times_overlap(time(8, 0), time(10, 0), time(12, 0), time(14, 0)) is False

    def test_adjacent_no_overlap(self):
        assert times_overlap(time(8, 0), time(12, 0), time(12, 0), time(16, 0)) is False

    def test_overlap(self):
        assert times_overlap(time(8, 0), time(14, 0), time(12, 0), time(18, 0)) is True


class TestIsEmployeeOnTimeOff:
    def test_no_time_off(self):
        shift_start = datetime(2025, 1, 20, 9, 0)
        shift_end = datetime(2025, 1, 20, 17, 0)
        assert is_employee_on_time_off(1, shift_start, shift_end, []) is False

    def test_on_time_off(self):
        shift_start = datetime(2025, 1, 20, 9, 0)
        shift_end = datetime(2025, 1, 20, 17, 0)
        time_off = [TimeOffRequest(
            employee_id=1,
            start_datetime=datetime(2025, 1, 20, 0, 0),
            end_datetime=datetime(2025, 1, 20, 23, 59),
        )]
        assert is_employee_on_time_off(1, shift_start, shift_end, time_off) is True

    def test_different_employee_not_affected(self):
        shift_start = datetime(2025, 1, 20, 9, 0)
        shift_end = datetime(2025, 1, 20, 17, 0)
        time_off = [TimeOffRequest(
            employee_id=2,
            start_datetime=datetime(2025, 1, 20, 0, 0),
            end_datetime=datetime(2025, 1, 20, 23, 59),
        )]
        assert is_employee_on_time_off(1, shift_start, shift_end, time_off) is False


class TestGetAvailabilityForSlot:
    def test_no_rules_returns_none(self):
        result = get_availability_for_slot(1, 0, time(10, 0), time(14, 0), [])
        assert result is None

    def test_all_day_unavailable(self):
        rules = [AvailabilityRule(
            employee_id=1, day_of_week=0,
            rule_type=AvailabilityType.UNAVAILABLE,
            start_time=None, end_time=None,
        )]
        result = get_availability_for_slot(1, 0, time(10, 0), time(14, 0), rules)
        assert result == AvailabilityType.UNAVAILABLE

    def test_available_window(self):
        rules = [AvailabilityRule(
            employee_id=1, day_of_week=0,
            rule_type=AvailabilityType.AVAILABLE,
            start_time=time(9, 0), end_time=time(18, 0),
        )]
        result = get_availability_for_slot(1, 0, time(10, 0), time(14, 0), rules)
        assert result == AvailabilityType.AVAILABLE

    def test_preferred_window(self):
        rules = [AvailabilityRule(
            employee_id=1, day_of_week=0,
            rule_type=AvailabilityType.PREFERRED,
            start_time=time(8, 0), end_time=time(14, 0),
        )]
        result = get_availability_for_slot(1, 0, time(10, 0), time(14, 0), rules)
        assert result == AvailabilityType.PREFERRED


class TestCanEmployeeWorkShift:
    def test_can_work_no_conflicts(self, basic_employee):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        
        can_work, reason = can_employee_work_shift(
            basic_employee, shift_start, shift_end, 1, [], [], []
        )
        assert can_work is True

    def test_cannot_work_wrong_department(self, basic_employee):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        
        can_work, reason = can_employee_work_shift(
            basic_employee, shift_start, shift_end, 99, [], [], []
        )
        assert can_work is False
        assert "department" in reason.lower()

    def test_cannot_work_on_time_off(self, basic_employee):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        time_off = [TimeOffRequest(
            employee_id=1,
            start_datetime=datetime.combine(monday, time(0, 0)),
            end_datetime=datetime.combine(monday, time(23, 59)),
        )]
        
        can_work, reason = can_employee_work_shift(
            basic_employee, shift_start, shift_end, 1, [], time_off, []
        )
        assert can_work is False

    def test_cannot_work_conflicting_shift(self, basic_employee):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        existing = [Shift(
            employee_id=1, store_id=1, department_id=1,
            start_datetime=datetime.combine(monday, time(12, 0)),
            end_datetime=datetime.combine(monday, time(20, 0)),
        )]
        
        can_work, reason = can_employee_work_shift(
            basic_employee, shift_start, shift_end, 1, [], [], existing
        )
        assert can_work is False


class TestGetAvailableEmployeesForSlot:
    def test_filters_by_department(self, three_employees):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        
        available = get_available_employees_for_slot(
            three_employees, shift_start, shift_end, 1, [], [], []
        )
        # Only emp 1 and 2 are in dept 1
        assert len(available) == 2
        emp_ids = [e.id for e, _ in available]
        assert 3 not in emp_ids

    def test_excludes_unavailable(self, three_employees):
        monday = get_test_monday()
        shift_start = datetime.combine(monday, time(9, 0))
        shift_end = datetime.combine(monday, time(17, 0))
        rules = [AvailabilityRule(
            employee_id=1, day_of_week=0,
            rule_type=AvailabilityType.UNAVAILABLE,
            start_time=None, end_time=None,
        )]
        
        available = get_available_employees_for_slot(
            three_employees, shift_start, shift_end, 1, rules, [], []
        )
        assert len(available) == 1
        assert available[0][0].id == 2