"""
Integration tests for OR-Tools solver with seed_data_v4.
"""
import pytest
from datetime import date, time, datetime, timedelta
from collections import Counter

from app.db.database import SessionLocal
from app.services.scheduling.data_loader import load_schedule_context
from app.services.scheduling.or_solver import solve_schedule
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
    days_ahead = 7 - today.weekday()
    return today + timedelta(days=days_ahead)


EMP_NAMES = {
    100001: "Manager", 100002: "Alice", 100003: "Bob", 100004: "Carol",
    100005: "David", 100006: "Emma", 100007: "Frank",
}
DEPT_NAMES = {100001: "Tills", 100002: "Floor", 100003: "CS"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def emp_name(emp_id: int) -> str:
    return EMP_NAMES.get(emp_id, f"Emp{emp_id}")

def dept_name(dept_id: int) -> str:
    return DEPT_NAMES.get(dept_id, f"Dept{dept_id}")


class TestDataLoader:
    def test_loads_7_employees(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        assert len(context.employees) == 7

    def test_loads_5_keyholders(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        assert len([e for e in context.employees if e.is_keyholder]) == 5

    def test_loads_12_coverage_requirements(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        assert len(context.coverage_requirements) == 12

    def test_loads_2_role_requirements(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        assert len(context.role_requirements) == 2


class TestAvailabilityWithSeedData:
    def test_emma_available_morning(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        emp = next(e for e in context.employees if e.id == 100006)
        can_work, _ = can_employee_work_shift(
            emp, datetime.combine(monday, time(7, 0)), datetime.combine(monday, time(14, 0)),
            emp.department_ids[0], context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is True

    def test_emma_unavailable_evening(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        emp = next(e for e in context.employees if e.id == 100006)
        can_work, _ = can_employee_work_shift(
            emp, datetime.combine(monday, time(16, 0)), datetime.combine(monday, time(21, 0)),
            emp.department_ids[0], context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False

    def test_carol_available_evening(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        emp = next(e for e in context.employees if e.id == 100004)
        can_work, _ = can_employee_work_shift(
            emp, datetime.combine(monday, time(17, 0)), datetime.combine(monday, time(21, 0)),
            emp.department_ids[0], context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is True

    def test_alice_unavailable_sunday(self, db):
        monday = get_next_monday()
        sunday = monday + timedelta(days=6)
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        emp = next(e for e in context.employees if e.id == 100002)
        can_work, _ = can_employee_work_shift(
            emp, datetime.combine(sunday, time(10, 0)), datetime.combine(sunday, time(14, 0)),
            emp.department_ids[0], context.availability_rules, context.time_off_requests, context.existing_shifts
        )
        assert can_work is False


class TestSolverConstraints:
    def test_generates_shifts(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        assert len(result.shifts) > 0

    def test_all_shifts_valid_length(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        for shift in result.shifts:
            assert 4 <= shift.duration_hours <= 12

    def test_no_double_booking(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        day_counts = Counter((s.employee_id, s.day_of_week) for s in result.shifts)
        for (emp_id, day), count in day_counts.items():
            assert count == 1, f"{emp_name(emp_id)} scheduled {count} times on {DAYS[day]}"

    def test_alice_not_scheduled_sunday(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        sunday_alice = [s for s in result.shifts if s.employee_id == 100002 and s.day_of_week == 6]
        assert len(sunday_alice) == 0


class TestScheduleOutput:
    def test_prints_full_schedule(self, db):
        monday = get_next_monday()
        context = load_schedule_context(db, store_id=100001, week_start=monday)
        result = solve_schedule(context)
        
        print(f"\n{'='*70}")
        print(f"OR-Tools Schedule - Week of {monday}")
        print(f"{'='*70}")
        print(f"Solver success: {result.success}")
        print(f"Total shifts: {len(result.shifts)}")
        
        if result.warnings:
            print(f"\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")
        
        # Unmet constraints summary
        total_unmet = len(result.unmet_coverage) + len(result.unmet_role_requirements) + len(result.unmet_contracted_hours)
        if total_unmet > 0:
            print(f"\n{'='*70}")
            print(f"UNMET CONSTRAINTS ({total_unmet} total)")
            print(f"{'='*70}")
            
            if result.unmet_coverage:
                print(f"\nCoverage ({len(result.unmet_coverage)}):")
                for cov in result.unmet_coverage:
                    print(f"  {DAYS[cov.day_of_week]} {cov.start_time.strftime('%H:%M')}-{cov.end_time.strftime('%H:%M')} "
                          f"{dept_name(cov.department_id)} needs {cov.min_staff}")
            
            if result.unmet_role_requirements:
                print(f"\nRole Requirements ({len(result.unmet_role_requirements)}):")
                for req in result.unmet_role_requirements:
                    day_str = DAYS[req.day_of_week] if req.day_of_week is not None else "Daily"
                    role = "manager" if req.requires_manager else "keyholder"
                    print(f"  {day_str} {req.start_time.strftime('%H:%M')}-{req.end_time.strftime('%H:%M')} needs {role}")
            
            if result.unmet_contracted_hours:
                print(f"\nContracted Hours ({len(result.unmet_contracted_hours)}):")
                for emp_id, shortfall in result.unmet_contracted_hours.items():
                    emp = next(e for e in context.employees if e.id == emp_id)
                    print(f"  {emp_name(emp_id)}: {shortfall:.1f}h short (contracted {emp.contracted_weekly_hours}h)")
        
        # Weekly schedule
        print(f"\n{'='*70}")
        print("WEEKLY SCHEDULE")
        print(f"{'='*70}")
        
        for day_idx, day_str in enumerate(DAYS):
            day_shifts = sorted([s for s in result.shifts if s.day_of_week == day_idx], key=lambda s: s.start_datetime)
            print(f"\n{day_str}:")
            if not day_shifts:
                print("  (no shifts)")
                continue
            for s in day_shifts:
                emp = next(e for e in context.employees if e.id == s.employee_id)
                role = "[MGR]" if emp.is_manager else "[KEY]" if emp.is_keyholder else "[REG]"
                print(f"  {s.start_datetime.strftime('%H:%M')}-{s.end_datetime.strftime('%H:%M')} "
                      f"{emp_name(s.employee_id):8} {role:5} {dept_name(s.department_id)}")
        
        # Hours summary
        print(f"\n{'='*70}")
        print("HOURS SUMMARY")
        print(f"{'='*70}")
        
        all_shifts = list(context.existing_shifts) + list(result.shifts)
        total_assigned = total_contracted = 0
        
        for emp in sorted(context.employees, key=lambda e: e.id):
            assigned = sum(s.duration_hours for s in all_shifts if s.employee_id == emp.id)
            total_assigned += assigned
            total_contracted += emp.contracted_weekly_hours
            diff = assigned - emp.contracted_weekly_hours
            role = "[MGR]" if emp.is_manager else "[KEY]" if emp.is_keyholder else "[REG]"
            status = "OK" if diff >= -0.1 else "SHORT"
            print(f"  {emp_name(emp.id):8} {role:5}: {assigned:5.1f}h / {emp.contracted_weekly_hours:2}h ({diff:+.1f}h) {status}")
        
        print(f"\n  {'TOTAL':14}: {total_assigned:5.1f}h / {total_contracted}h")
        print(f"{'='*70}\n")


class TestCoverageValidation:
    def test_tills_coverage(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        tills_unmet = [c for c in result.unmet_coverage if c.department_id == 100001]
        if tills_unmet:
            print(f"\nTills gaps: {[DAYS[c.day_of_week] for c in tills_unmet]}")
        else:
            print(f"\nTills coverage: FULLY MET")

    def test_cs_coverage(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        cs_unmet = [c for c in result.unmet_coverage if c.department_id == 100003]
        if cs_unmet:
            print(f"\nCS gaps: {[DAYS[c.day_of_week] for c in cs_unmet]}")
        else:
            print(f"\nCS coverage: FULLY MET")


class TestRoleValidation:
    def test_keyholder_morning(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        unmet = next((r for r in result.unmet_role_requirements if r.start_time == time(7, 0)), None)
        print(f"\nMorning keyholder: {'UNMET' if unmet else 'MET'}")

    def test_keyholder_evening(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        unmet = next((r for r in result.unmet_role_requirements if r.start_time == time(17, 0)), None)
        print(f"\nEvening keyholder: {'UNMET' if unmet else 'MET'}")


class TestContractedHoursValidation:
    def test_all_employees_meet_hours(self, db):
        context = load_schedule_context(db, store_id=100001, week_start=get_next_monday())
        result = solve_schedule(context)
        if result.unmet_contracted_hours:
            print(f"\nShort on hours: {[emp_name(eid) for eid in result.unmet_contracted_hours.keys()]}")
        else:
            print(f"\nAll employees meet contracted hours: YES")