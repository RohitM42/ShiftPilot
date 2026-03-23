"""
Seed script for ShiftPilot - Generate published shifts for testing.

Creates PUBLISHED shifts for 5 weeks (current week ± 2 weeks).
Respects employee availability windows and department assignments from seed_data_v4.

Run with: python -m scripts.seed_shifts
"""

import sys
import random
from typing import Optional
from datetime import date, time, datetime, timedelta
from sqlalchemy import text
from app.db.database import SessionLocal
from app.db.models.shifts import Shifts, ShiftStatus, ShiftSource


# ── Employee definitions (from seed_data_v4) ─────────────────────────

EMPLOYEES = {
    100001: {
        "name": "Manager",
        "contracted_hours": 40,
        "departments": [100001, 100002, 100003],
        "availability": {d: (time(6, 0), time(22, 0)) for d in range(7)},
    },
    100002: {
        "name": "Alice",
        "contracted_hours": 32,
        "departments": [100001, 100003],
        "availability": {
            **{d: (time(7, 0), time(17, 0)) for d in range(5)},
            5: (time(8, 0), time(14, 0)),
            # 6 (Sun) unavailable
        },
    },
    100003: {
        "name": "Bob",
        "contracted_hours": 24,
        "departments": [100002, 100001],
        "availability": {
            **{d: (time(8, 0), time(18, 0)) for d in range(6)},
            # 6 (Sun) unavailable
        },
    },
    100004: {
        "name": "Carol",
        "contracted_hours": 24,
        "departments": [100003, 100001],
        "availability": {d: (time(13, 0), time(22, 0)) for d in range(7)},
    },
    100005: {
        "name": "David",
        "contracted_hours": 24,
        "departments": [100003, 100001],
        "availability": {
            **{d: (time(9, 0), time(18, 0)) for d in range(5)},
            # 5,6 (Sat,Sun) unavailable
        },
    },
    100006: {
        "name": "Emma",
        "contracted_hours": 32,
        "departments": [100001, 100002],
        "availability": {d: (time(6, 0), time(15, 0)) for d in range(7)},
    },
    100007: {
        "name": "Frank",
        "contracted_hours": 32,
        "departments": [100001, 100002, 100003],
        "availability": {d: (time(6, 0), time(22, 0)) for d in range(7)},
    },
}

STORE_ID = 100001
SHIFT_DURATIONS = [6, 7, 8]  # hours


def get_week_monday(offset: int = 0) -> date:
    """Get Monday of the current week + offset weeks."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=offset)


def generate_shift_for_employee(emp_id: int, day_date: date, day_of_week: int) -> Optional[dict]:
    """Generate a single shift for an employee on a given day, or None if unavailable."""
    emp = EMPLOYEES[emp_id]
    avail = emp["availability"].get(day_of_week)
    if not avail:
        return None

    avail_start, avail_end = avail
    avail_start_h = avail_start.hour
    avail_end_h = avail_end.hour

    duration = random.choice(SHIFT_DURATIONS)
    avail_window = avail_end_h - avail_start_h
    if duration > avail_window:
        duration = avail_window
    if duration < 4:
        return None

    max_start = avail_end_h - duration
    start_hour = random.randint(avail_start_h, max_start)

    start_dt = datetime.combine(day_date, time(start_hour, 0))
    end_dt = start_dt + timedelta(hours=duration)

    dept_id = emp["departments"][0]  # primary department

    return {
        "store_id": STORE_ID,
        "department_id": dept_id,
        "employee_id": emp_id,
        "start_datetime_utc": start_dt,
        "end_datetime_utc": end_dt,
        "status": ShiftStatus.PUBLISHED,
        "source": ShiftSource.MANUAL,
        "created_by_user_id": 100001,  # admin
    }


def generate_shifts() -> list[dict]:
    """Generate shifts for 5 weeks."""
    shifts = []

    for week_offset in range(-2, 3):
        monday = get_week_monday(week_offset)

        for emp_id, emp in EMPLOYEES.items():
            weekly_hours = 0
            target_hours = emp["contracted_hours"]

            # shuffle days so we don't always fill Mon first
            days = list(range(7))
            random.shuffle(days)

            for day_of_week in days:
                if weekly_hours >= target_hours:
                    break

                day_date = monday + timedelta(days=day_of_week)
                shift = generate_shift_for_employee(emp_id, day_date, day_of_week)
                if shift:
                    shift_hours = (shift["end_datetime_utc"] - shift["start_datetime_utc"]).seconds / 3600
                    if weekly_hours + shift_hours <= target_hours + 2:  # small buffer
                        shifts.append(shift)
                        weekly_hours += shift_hours

    return shifts


def main():
    print("\n" + "=" * 50)
    print("ShiftPilot Shift Seeder")
    print("=" * 50 + "\n")

    response = input("This will DELETE ALL EXISTING SHIFTS. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        sys.exit(0)

    db = SessionLocal()

    try:
        # Clear existing shifts
        print("Truncating shifts table...")
        db.execute(text("TRUNCATE TABLE shifts RESTART IDENTITY CASCADE;"))
        db.commit()

        # Generate and insert
        print("Generating shifts...")
        shift_data = generate_shifts()

        for data in shift_data:
            db.add(Shifts(**data))

        db.commit()

        # Reset sequence
        db.execute(text("SELECT setval('shifts_id_seq', (SELECT COALESCE(MAX(id), 1) FROM shifts));"))
        db.commit()

        print(f"\nSeeded {len(shift_data)} shifts across 5 weeks.")
        print(f"Week range: {get_week_monday(-2)} to {get_week_monday(2) + timedelta(days=6)}")
        print("=" * 50 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()