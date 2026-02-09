"""
Context loader for AI service.
Loads org context from DB for LLM prompt construction.
Follows same pattern as scheduling/data_loader.py.
"""

from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.models.employees import Employees, EmploymentStatus
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.availability_rules import AvailabilityRules
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.store_departments import StoreDepartment
from app.db.models.users import Users


def load_employee_context(db: Session, user_id: int) -> Optional[dict]:
    """Load employee info for the requesting user. Used for employee-facing requests."""
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        return None

    employee = db.query(Employees).filter(
        Employees.user_id == user_id,
        Employees.employment_status == EmploymentStatus.ACTIVE,
    ).first()
    if not employee:
        return None

    dept_rows = db.query(EmployeeDepartments).filter(
        EmployeeDepartments.employee_id == employee.id
    ).all()

    departments = []
    for d in dept_rows:
        dept = db.query(Departments).filter(Departments.id == d.department_id).first()
        if dept:
            departments.append({
                "department_id": dept.id,
                "name": dept.name,
                "is_primary": d.is_primary,
            })

    avail_rules = db.query(AvailabilityRules).filter(
        AvailabilityRules.employee_id == employee.id,
        AvailabilityRules.active == True,
    ).all()

    availability = []
    for r in avail_rules:
        availability.append({
            "day_of_week": r.day_of_week,
            "start_time": r.start_time_local.isoformat() if r.start_time_local else None,
            "end_time": r.end_time_local.isoformat() if r.end_time_local else None,
            "rule_type": r.rule_type.value,
        })

    return {
        "employee_id": employee.id,
        "user_id": user_id,
        "store_id": employee.store_id,
        "name": f"{user.firstname} {user.surname}",
        "is_keyholder": employee.is_keyholder,
        "is_manager": employee.is_manager,
        "contracted_weekly_hours": employee.contracted_weekly_hours,
        "departments": departments,
        "current_availability": availability,
    }


def load_store_context(db: Session, store_id: int) -> Optional[dict]:
    """Load store info including departments. Used for manager/admin requests."""
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        return None

    store_depts = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == store_id
    ).all()

    departments = []
    for sd in store_depts:
        dept = db.query(Departments).filter(Departments.id == sd.department_id).first()
        if dept:
            departments.append({"department_id": dept.id, "name": dept.name})

    return {
        "store_id": store.id,
        "store_name": store.name,
        "departments": departments,
    }


def load_coverage_context(db: Session, store_id: int, department_id: Optional[int] = None) -> List[dict]:
    """Load current coverage requirements. Used for coverage change requests."""
    query = db.query(CoverageRequirements).filter(
        CoverageRequirements.store_id == store_id,
        CoverageRequirements.active == True,
    )
    if department_id:
        query = query.filter(CoverageRequirements.department_id == department_id)

    rows = query.all()
    return [
        {
            "id": r.id,
            "department_id": r.department_id,
            "day_of_week": r.day_of_week,
            "start_time": r.start_time_local.isoformat() if r.start_time_local else None,
            "end_time": r.end_time_local.isoformat() if r.end_time_local else None,
            "min_staff": r.min_staff,
            "max_staff": r.max_staff,
        }
        for r in rows
    ]


def load_store_employees_context(db: Session, store_id: int) -> List[dict]:
    """Load employee names/ids for a store. Used for admin requests that reference employees by name."""
    employees = db.query(Employees).filter(
        Employees.store_id == store_id,
        Employees.employment_status == EmploymentStatus.ACTIVE,
    ).all()

    result = []
    for emp in employees:
        user = db.query(Users).filter(Users.id == emp.user_id).first()
        if user:
            result.append({
                "employee_id": emp.id,
                "name": f"{user.firstname} {user.surname}",
                "is_manager": emp.is_manager,
                "is_keyholder": emp.is_keyholder,
            })
    return result