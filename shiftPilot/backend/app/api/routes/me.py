from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.db.models.users import Users
from app.db.models.employees import Employees
from app.db.models.shifts import Shifts
from app.db.models.availability_rules import AvailabilityRules
from app.db.models.time_off_requests import TimeOffRequests
from app.db.models.employee_departments import EmployeeDepartments
from app.schemas.shifts import ShiftResponse
from app.schemas.availability_rules import AvailabilityRuleResponse
from app.schemas.time_off_requests import TimeOffRequestResponse
from app.schemas.employee_departments import EmployeeDepartmentResponse
from app.schemas.employees import EmployeeResponse

router = APIRouter(prefix="/me", tags=["me"])


def get_current_employee(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> Employees:
    """Helper to get employee record for current user"""
    employee = db.query(Employees).filter(Employees.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="No employee record found for current user")
    return employee


@router.get("/employee", response_model=EmployeeResponse)
def get_my_employee_record(
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's employee record"""
    return employee


@router.get("/shifts", response_model=List[ShiftResponse])
def get_my_shifts(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's shifts"""
    query = db.query(Shifts).filter(Shifts.employee_id == employee.id)
    
    if start_date:
        query = query.filter(Shifts.start_datetime_utc >= start_date)
    if end_date:
        query = query.filter(Shifts.end_datetime_utc <= end_date)
    
    return query.order_by(Shifts.start_datetime_utc).all()


@router.get("/availability-rules", response_model=List[AvailabilityRuleResponse])
def get_my_availability_rules(
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's availability rules"""
    return db.query(AvailabilityRules).filter(AvailabilityRules.employee_id == employee.id).all()


@router.get("/time-off-requests", response_model=List[TimeOffRequestResponse])
def get_my_time_off_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's time off requests"""
    query = db.query(TimeOffRequests).filter(TimeOffRequests.employee_id == employee.id)
    
    if status:
        query = query.filter(TimeOffRequests.status == status)
    
    return query.order_by(TimeOffRequests.start_date.desc()).all()


@router.get("/departments", response_model=List[EmployeeDepartmentResponse])
def get_my_departments(
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get departments current user is assigned to"""
    return db.query(EmployeeDepartments).filter(EmployeeDepartments.employee_id == employee.id).all()