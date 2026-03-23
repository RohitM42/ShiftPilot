"""
Test file for seed_data_v4 (simplified version)
"""
import pytest
from datetime import date, time, datetime, timedelta

from app.db.database import SessionLocal
from app.services.scheduling.data_loader import load_schedule_context
from app.services.scheduling.solver import solve_schedule
from app.services.scheduling.availability import can_employee_work_shift


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_next_monday() -> date:
    today = date.today()
    days_ahead = 7 - today.weekday()  # next Monday
    return today + timedelta(days=days_ahead)


class TestDataLoader:

    def test_loads_store_1_employees(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # Store 100001 has 7 active employees in v5
        assert len(context.employees) == 7
        
        emp_ids = {e.id for e in context.employees}
        assert emp_ids == {100001, 100002, 100003, 100004, 100005, 100006, 100007}

    def test_loads_manager_flags_correctly(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        manager = next(e for e in context.employees if e.id == 100001)
        assert manager.is_manager is True
        assert manager.is_keyholder is True
        assert manager.contracted_weekly_hours == 40

    def test_loads_keyholders_correctly(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        keyholders = [e for e in context.employees if e.is_keyholder]
        # Manager + Alice + Carol + Emma + Frank = 5 keyholders
        assert len(keyholders) == 5

    def test_loads_coverage_requirements(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # Tills (7 days) + CS (5 days Mon-Fri) = 12 requirements
        assert len(context.coverage_requirements) == 12

    def test_loads_role_requirements(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # 2 role requirements (keyholder 7-10am, 17-21pm)
        assert len(context.role_requirements) == 2

    def test_no_existing_shifts(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # Clean slate - no existing shifts
        assert len(context.existing_shifts) == 0


class TestAvailabilityWithSeedData:

    def test_emma_available_morning(self, db):
        """Emma (100006) is morning specialist, available 6am-15pm."""
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100006)
        shift_start = datetime.combine(monday, time(7, 0))
        shift_end = datetime.combine(monday, time(14, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is True

    def test_emma_unavailable_evening(self, db):
        """Emma (100006) is not available in evenings."""
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100006)
        shift_start = datetime.combine(monday, time(16, 0))
        shift_end = datetime.combine(monday, time(21, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False

    def test_carol_available_evening(self, db):
        """Carol (100004) is evening specialist, available 13pm-22pm."""
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100004)
        shift_start = datetime.combine(monday, time(17, 0))
        shift_end = datetime.combine(monday, time(21, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is True

    def test_carol_unavailable_morning(self, db):
        """Carol (100004) is not available in mornings."""
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100004)
        shift_start = datetime.combine(monday, time(7, 0))
        shift_end = datetime.combine(monday, time(12, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False

    def test_alice_unavailable_sunday(self, db):
        """Alice (100002) is unavailable on Sundays."""
        monday = get_next_monday()
        sunday = monday + timedelta(days=6)
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100002)
        shift_start = datetime.combine(sunday, time(10, 0))
        shift_end = datetime.combine(sunday, time(14, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False


class TestSolverWithSeedData:

    def test_generates_shifts_for_store_1(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        assert len(result.shifts) > 0
        for shift in result.shifts:
            assert shift.store_id == 100001

    def test_all_shifts_valid_length(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        valid_lengths = {4, 5, 6, 7, 8, 9, 10, 11, 12}
        for shift in result.shifts:
            assert shift.duration_hours in valid_lengths, \
                f"Shift {shift} has invalid length {shift.duration_hours}h"
            assert shift.duration_hours >= 4, \
                f"Shift {shift} is under 4 hours"

    def test_no_employee_double_booked(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        from collections import Counter
        day_counts = Counter((s.employee_id, s.day_of_week) for s in result.shifts)
        for (emp_id, day), count in day_counts.items():
            assert count == 1, f"Employee {emp_id} scheduled {count} times on day {day}"

    def test_unavailable_employee_not_scheduled(self, db):
        """Alice (100002) should not be scheduled on Sunday."""
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        sunday_shifts_alice = [
            s for s in result.shifts 
            if s.employee_id == 100002 and s.day_of_week == 6
        ]
        assert len(sunday_shifts_alice) == 0

    def test_prints_schedule_summary(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        print(f"\n{'='*60}")
        print(f"Store 100001 Schedule - Week of {monday} (v5 Simplified)")
        print(f"{'='*60}")
        print(f"Shifts generated: {len(result.shifts)}")
        print(f"Success: {result.success}")
        
        if result.unmet_coverage:
            print(f"\nUnmet coverage ({len(result.unmet_coverage)}):")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for cov in result.unmet_coverage:
                print(f"  {days[cov.day_of_week]} {cov.start_time}-{cov.end_time} "
                      f"Dept {cov.department_id} needs {cov.min_staff} staff")
        
        if result.unmet_role_requirements:
            print(f"\nUnmet role requirements ({len(result.unmet_role_requirements)}):")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for req in result.unmet_role_requirements:
                day_str = days[req.day_of_week] if req.day_of_week is not None else "Every day"
                role = "manager" if req.requires_manager else "keyholder" if req.requires_keyholder else "unknown"
                print(f"  {day_str} {req.start_time}-{req.end_time} needs {role}")
        
        if result.unmet_contracted_hours:
            print(f"\nHour shortfalls:")
            for emp_id, shortfall in result.unmet_contracted_hours.items():
                emp = next(e for e in context.employees if e.id == emp_id)
                print(f"  Emp {emp_id}: {shortfall}h short (contracted {emp.contracted_weekly_hours}h)")
        
        # Employee name mapping for v5
        emp_names = {
            100001: "Manager",
            100002: "Alice",
            100003: "Bob",
            100004: "Carol",
            100005: "David",
            100006: "Emma",
            100007: "Frank",
        }
        
        dept_names = {
            100001: "Tills",
            100002: "Floor",
            100003: "CS",
        }
        
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day_idx, day_name in enumerate(days):
            day_shifts = sorted(
                [s for s in result.shifts if s.day_of_week == day_idx],
                key=lambda s: s.start_datetime
            )
            if day_shifts:
                print(f"\n{day_name}:")
                for s in day_shifts:
                    emp = next(e for e in context.employees if e.id == s.employee_id)
                    role = "[MGR]" if emp.is_manager else "[KEY]" if emp.is_keyholder else ""
                    name = emp_names.get(s.employee_id, f"Emp{s.employee_id}")
                    dept = dept_names.get(s.department_id, f"Dept{s.department_id}")
                    print(f"  {s.start_datetime.strftime('%H:%M')}-{s.end_datetime.strftime('%H:%M')} "
                          f"{name:8} {role:5} {dept}")
        
        print(f"\n{'='*60}")
        print("Hours Summary:")
        all_shifts = list(context.existing_shifts) + list(result.shifts)
        total_assigned = 0
        total_contracted = 0
        for emp in sorted(context.employees, key=lambda e: e.id):
            assigned = sum(s.duration_hours for s in all_shifts if s.employee_id == emp.id)
            total_assigned += assigned
            total_contracted += emp.contracted_weekly_hours
            diff = assigned - emp.contracted_weekly_hours
            sign = "+" if diff >= 0 else ""
            role_tag = "[MGR]" if emp.is_manager else "[KEY]" if emp.is_keyholder else ""
            name = emp_names.get(emp.id, f"Emp{emp.id}")
            print(f"  {name:8}: {assigned:5.1f}h / {emp.contracted_weekly_hours}h ({sign}{diff:.1f}h) {role_tag}")
        
        print(f"\n  TOTAL:    {total_assigned:.1f}h / {total_contracted}h contracted")
        print(f"{'='*60}\n")
        
        # This test always passes - it's for output
        assert True