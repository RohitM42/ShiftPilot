"""
Data loader for scheduling service.
Fetches all relevant data from the database and converts to internal types.
"""

from datetime import date, datetime, timedelta, time
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.models.employees import Employees, EmploymentStatus
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.availability_rules import AvailabilityRules, AvailabilityRuleType
from app.db.models.time_off_requests import TimeOffRequests, TimeOffStatus
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.role_requirements import RoleRequirements
from app.db.models.shifts import Shifts, ShiftStatus

from .types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    TimeOffRequest,
    CoverageRequirement,
    RoleRequirement,
    Shift,
    ScheduleContext,
)


def load_employees(db: Session, store_id: int) -> list[Employee]:
    """Load active employees for a store with their department assignments."""
    
    # Get active employees for the store
    stmt = select(Employees).where(
        and_(
            Employees.store_id == store_id,
            Employees.employment_status == EmploymentStatus.ACTIVE
        )
    )
    employee_rows = db.execute(stmt).scalars().all()
    
    employees = []
    for emp in employee_rows:
        # Get department assignments
        dept_stmt = select(EmployeeDepartments).where(
            EmployeeDepartments.employee_id == emp.id
        )
        dept_rows = db.execute(dept_stmt).scalars().all()
        
        department_ids = [d.department_id for d in dept_rows]
        primary_dept = next(
            (d.department_id for d in dept_rows if d.is_primary),
            department_ids[0] if department_ids else None
        )
        
        employees.append(Employee(
            id=emp.id,
            store_id=emp.store_id,
            is_keyholder=emp.is_keyholder,
            is_manager=emp.is_manager,
            contracted_weekly_hours=emp.contracted_weekly_hours,
            department_ids=department_ids,
            primary_department_id=primary_dept,
        ))
    
    return employees


def load_availability_rules(db: Session, employee_ids: list[int]) -> list[AvailabilityRule]:
    """Load active availability rules for a set of employees."""
    
    if not employee_ids:
        return []
    
    stmt = select(AvailabilityRules).where(
        and_(
            AvailabilityRules.employee_id.in_(employee_ids),
            AvailabilityRules.active == True
        )
    )
    rows = db.execute(stmt).scalars().all()
    
    return [
        AvailabilityRule(
            employee_id=r.employee_id,
            day_of_week=r.day_of_week,
            rule_type=AvailabilityType(r.rule_type.value),
            start_time=r.start_time_local,
            end_time=r.end_time_local,
        )
        for r in rows
    ]


def load_time_off_requests(
    db: Session, 
    employee_ids: list[int], 
    week_start: date
) -> list[TimeOffRequest]:
    """Load approved time off requests that overlap with the schedule week."""
    
    if not employee_ids:
        return []
    
    week_end = week_start + timedelta(days=7)
    week_start_dt = datetime.combine(week_start, time.min)
    week_end_dt = datetime.combine(week_end, time.min)
    
    stmt = select(TimeOffRequests).where(
        and_(
            TimeOffRequests.employee_id.in_(employee_ids),
            TimeOffRequests.status == TimeOffStatus.APPROVED,
            TimeOffRequests.start_date < week_end_dt,
            TimeOffRequests.end_date > week_start_dt,
        )
    )
    rows = db.execute(stmt).scalars().all()
    
    return [
        TimeOffRequest(
            employee_id=r.employee_id,
            start_datetime=r.start_date,
            end_datetime=r.end_date,
        )
        for r in rows
    ]


def load_coverage_requirements(db: Session, store_id: int) -> list[CoverageRequirement]:
    """Load active coverage requirements for a store."""
    
    stmt = select(CoverageRequirements).where(
        and_(
            CoverageRequirements.store_id == store_id,
            CoverageRequirements.active == True
        )
    )
    rows = db.execute(stmt).scalars().all()
    
    return [
        CoverageRequirement(
            id=r.id,
            store_id=r.store_id,
            department_id=r.department_id,
            day_of_week=r.day_of_week,
            start_time=r.start_time_local,
            end_time=r.end_time_local,
            min_staff=r.min_staff,
            max_staff=r.max_staff,
        )
        for r in rows
    ]


def load_role_requirements(db: Session, store_id: int) -> list[RoleRequirement]:
    """Load active role requirements for a store."""
    
    stmt = select(RoleRequirements).where(
        and_(
            RoleRequirements.store_id == store_id,
            RoleRequirements.active == True
        )
    )
    rows = db.execute(stmt).scalars().all()
    
    return [
        RoleRequirement(
            id=r.id,
            store_id=r.store_id,
            department_id=r.department_id,
            day_of_week=r.day_of_week,
            start_time=r.start_time_local,
            end_time=r.end_time_local,
            requires_keyholder=r.requires_keyholder,
            requires_manager=r.requires_manager,
            min_manager_count=r.min_manager_count,
        )
        for r in rows
    ]


def load_existing_shifts(
    db: Session, 
    store_id: int, 
    week_start: date
) -> list[Shift]:
    """Load existing non-cancelled shifts for the week (for conflict detection)."""
    
    week_start_dt = datetime.combine(week_start, time.min)
    week_end_dt = datetime.combine(week_start + timedelta(days=7), time.min)
    
    stmt = select(Shifts).where(
        and_(
            Shifts.store_id == store_id,
            Shifts.status != ShiftStatus.CANCELLED,
            Shifts.start_datetime_utc >= week_start_dt,
            Shifts.start_datetime_utc < week_end_dt,
        )
    )
    rows = db.execute(stmt).scalars().all()
    
    return [
        Shift(
            employee_id=s.employee_id,
            store_id=s.store_id,
            department_id=s.department_id,
            start_datetime=s.start_datetime_utc.replace(tzinfo=None),
            end_datetime=s.end_datetime_utc.replace(tzinfo=None),
        )
        for s in rows
    ]


def load_schedule_context(db: Session, store_id: int, week_start: date) -> ScheduleContext:
    """
    Load all data needed to generate a schedule for a store/week.
    
    returns scheduleContext for a given store/week
    """
    # Validate week_start is a Monday
    if week_start.weekday() != 0:
        raise ValueError(f"week_start must be a Monday, got {week_start} ({week_start.strftime('%A')})")
    
    employees = load_employees(db, store_id)
    employee_ids = [e.id for e in employees]
    
    return ScheduleContext(
        store_id=store_id,
        week_start=week_start,
        employees=employees,
        availability_rules=load_availability_rules(db, employee_ids),
        time_off_requests=load_time_off_requests(db, employee_ids, week_start),
        coverage_requirements=load_coverage_requirements(db, store_id),
        role_requirements=load_role_requirements(db, store_id),
        existing_shifts=load_existing_shifts(db, store_id, week_start),
    )