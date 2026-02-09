import pytest
from datetime import date, time, datetime, timedelta

from app.db.database import SessionLocal
from app.services.scheduling.data_loader import load_schedule_context
from app.services.scheduling.solver import solve_schedule
from app.services.scheduling.availability import can_employee_work_shift

# Test valid for seed data v1-v3

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
        
        # Store 100001 has 9 active employees
        assert len(context.employees) == 9
        
        emp_ids = {e.id for e in context.employees}
        assert emp_ids == {100001, 100003, 100004, 100005, 100006, 100010, 100011, 100012, 100013}

    def test_loads_store_2_excludes_on_leave(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100002, week_start=monday)
        
        # Store 100002 has 4 employees but 100009 is ON_LEAVE
        emp_ids = {e.id for e in context.employees}
        assert 100009 not in emp_ids
        assert len(context.employees) == 3

    def test_loads_manager_flags_correctly(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        manager = next(e for e in context.employees if e.id == 100001)
        assert manager.is_manager is True
        assert manager.is_keyholder is True
        assert manager.contracted_weekly_hours == 40

    def test_loads_availability_rules(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # Employee 100003 has Mon-Fri available, Sat-Sun unavailable
        emp_rules = [r for r in context.availability_rules if r.employee_id == 100003]
        assert len(emp_rules) == 7  # 5 available + 2 unavailable

    def test_loads_coverage_requirements(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # store 100001 has coverage for dept 100001 (7 days) + dept 100004 (6 days)
        assert len(context.coverage_requirements) == 13

    def test_loads_role_requirements(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        # Store 100001 has 2 role requirements (keyholder 6-10, 18-22)
        assert len(context.role_requirements) == 2


class TestAvailabilityWithSeedData:

    def test_employee_100003_available_weekday(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100003)
        shift_start = datetime.combine(monday, time(10, 0))
        shift_end = datetime.combine(monday, time(16, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is True

    def test_employee_100003_unavailable_weekend(self, db):
        monday = get_next_monday()
        saturday = monday + timedelta(days=5)
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100003)
        shift_start = datetime.combine(saturday, time(10, 0))
        shift_end = datetime.combine(saturday, time(16, 0))
        
        can_work, _ = can_employee_work_shift(
            emp, shift_start, shift_end, emp.department_ids[0],
            context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False

    def test_employee_100007_unavailable_wednesday(self, db):
        monday = get_next_monday()
        wednesday = monday + timedelta(days=2)
        context = load_schedule_context(db, store_id=100002, week_start=monday)
        
        emp = next(e for e in context.employees if e.id == 100007)
        shift_start = datetime.combine(wednesday, time(10, 0))
        shift_end = datetime.combine(wednesday, time(16, 0))
        
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
        
        # Allow flexible shift lengths: 4-12h for managers, 4-9h for regulars
        # Standard lengths preferred: 4, 6, 8, 10
        # Fallback lengths allowed: 5, 7, 9, 11, 12
        valid_lengths = {4, 5, 6, 7, 8, 9, 10, 11, 12}
        for shift in result.shifts:
            assert shift.duration_hours in valid_lengths, \
                f"Shift {shift} has invalid length {shift.duration_hours}h"
            # Ensure minimum shift length
            assert shift.duration_hours >= 4, \
                f"Shift {shift} is under 4 hours"

    def test_no_employee_double_booked(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        from collections import Counter
        day_counts = Counter((s.employee_id, s.day_of_week) for s in result.shifts)
        for (emp_id, day), count in day_counts.items():
            assert count == 1

    def test_unavailable_employee_not_scheduled(self, db):
        monday = get_next_monday()
        saturday = monday + timedelta(days=5)
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        # Employee 100003 unavailable weekends
        saturday_shifts_100003 = [
            s for s in result.shifts 
            if s.employee_id == 100003 and s.day_of_week == 5
        ]
        assert len(saturday_shifts_100003) == 0

    def test_prints_schedule_summary(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        
        result = solve_schedule(context)
        
        print(f"\n{'='*50}")
        print(f"Store 100001 Schedule - Week of {monday}")
        print(f"{'='*50}")
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
                    print(f"  {s.start_datetime.strftime('%H:%M')}-{s.end_datetime.strftime('%H:%M')} "
                          f"Emp {s.employee_id} {role} Dept {s.department_id}")
        
        print(f"{'='*50}\n")
        
        print("Hours Summary:")
        # Combine existing shifts with new shifts for total hours
        all_shifts = list(context.existing_shifts) + list(result.shifts)
        for emp in sorted(context.employees, key=lambda e: e.id):
            assigned = sum(s.duration_hours for s in all_shifts if s.employee_id == emp.id)
            diff = assigned - emp.contracted_weekly_hours
            sign = "+" if diff >= 0 else ""
            role_tag = "[MGR]" if emp.is_manager else "[KEY]" if emp.is_keyholder else ""
            print(f"  Emp {emp.id}: {assigned}h / {emp.contracted_weekly_hours}h ({sign}{diff}h) {role_tag}")
        print(f"\n{'='*50}")
        
        assert True  # Always passes, just for output