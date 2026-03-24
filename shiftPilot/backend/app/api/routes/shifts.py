from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time

from app.api.deps import get_db, get_current_user, require_manager_or_admin, check_store_access, get_accessible_store_ids
from app.db.models.shifts import Shifts, ShiftStatus
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.shifts import ShiftCreate, ShiftUpdate, ShiftResponse, ShiftWithViolationsResponse
from app.services.scheduling.availability import check_min_rest, check_rolling_window
from app.services.scheduling.types import Shift as SchedulerShift

router = APIRouter(prefix="/shifts", tags=["shifts"])


def _load_scheduler_shifts(
    db: Session,
    employee_id: int,
    around_date: datetime,
    exclude_shift_id: Optional[int] = None,
) -> list[SchedulerShift]:
    """Load non-cancelled shifts for an employee in a ±7-day window, converted to internal type."""
    window_start = datetime.combine((around_date - timedelta(days=7)).date(), time(0, 0, 0))
    window_end = datetime.combine((around_date + timedelta(days=7)).date(), time(23, 59, 59))
    query = db.query(Shifts).filter(
        Shifts.employee_id == employee_id,
        Shifts.status != ShiftStatus.CANCELLED,
        Shifts.start_datetime_utc >= window_start,
        Shifts.start_datetime_utc <= window_end,
    )
    if exclude_shift_id is not None:
        query = query.filter(Shifts.id != exclude_shift_id)
    rows = query.all()
    return [
        SchedulerShift(
            employee_id=s.employee_id,
            store_id=s.store_id,
            department_id=s.department_id,
            start_datetime=s.start_datetime_utc.replace(tzinfo=None),
            end_datetime=s.end_datetime_utc.replace(tzinfo=None),
        )
        for s in rows
    ]


@router.post("", response_model=ShiftWithViolationsResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    # check user has access to this store
    if not check_store_access(db, current_user, payload.store_id):
        raise HTTPException(status_code=403, detail="No access to this store")

    store = db.query(Stores).filter(Stores.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    department = db.query(Departments).filter(
        Departments.id == payload.department_id,
        Departments.active == True
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    new_start = payload.start_datetime_utc.replace(tzinfo=None)
    new_end = payload.end_datetime_utc.replace(tzinfo=None)
    existing = _load_scheduler_shifts(db, payload.employee_id, payload.start_datetime_utc)
    violations = (
        check_min_rest(payload.employee_id, new_start, new_end, existing)
        + check_rolling_window(payload.employee_id, new_start.date(), existing)
    )

    shift = Shifts(**payload.model_dump(), created_by_user_id=current_user.id)
    db.add(shift)
    db.commit()
    db.refresh(shift)
    response = ShiftWithViolationsResponse.model_validate(shift)
    response.violations = violations
    return response


@router.get("", response_model=List[ShiftResponse])
def list_shifts(
    store_id: Optional[int] = None,
    department_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    # get stores user can access
    accessible_stores = get_accessible_store_ids(db, current_user)
    
    query = db.query(Shifts)
    
    # filter by accessible stores (unless global admin)
    if accessible_stores is not None:
        if store_id and store_id not in accessible_stores:
            raise HTTPException(status_code=403, detail="No access to this store")
        query = query.filter(Shifts.store_id.in_(accessible_stores))
    
    #optional filters
    if store_id:
        query = query.filter(Shifts.store_id == store_id)
    if department_id:
        query = query.filter(Shifts.department_id == department_id)
    if employee_id:
        query = query.filter(Shifts.employee_id == employee_id)
    if start_date:
        query = query.filter(Shifts.start_datetime_utc >= start_date)
    if end_date:
        query = query.filter(Shifts.end_datetime_utc <= end_date)

    return query.order_by(Shifts.start_datetime_utc).offset(skip).limit(limit).all()


@router.get("/store-schedule", response_model=List[ShiftResponse])
def get_store_schedule(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    employee = db.query(Employees).filter(Employees.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=403, detail="No employee record found")

    query = db.query(Shifts).filter(
        Shifts.store_id == employee.store_id,
        Shifts.status == ShiftStatus.PUBLISHED,
    )
    if start_date:
        query = query.filter(Shifts.start_datetime_utc >= start_date)
    if end_date:
        query = query.filter(Shifts.end_datetime_utc <= end_date)

    return query.order_by(Shifts.start_datetime_utc).limit(500).all()


@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    shift = db.query(Shifts).filter(Shifts.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Check access
    accessible_stores = get_accessible_store_ids(db, current_user)
    
    # Get employee record for current user
    employee = db.query(Employees).filter(Employees.user_id == current_user.id).first()
    is_own_shift = employee and shift.employee_id == employee.id
    
    if accessible_stores is None:  # Global admin
        return shift
    if shift.store_id in accessible_stores:  # Store manager/admin
        return shift
    if is_own_shift:  # Own shift
        return shift
    
    raise HTTPException(status_code=403, detail="No access to this shift")


@router.put("/{shift_id}", response_model=ShiftWithViolationsResponse)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    shift = db.query(Shifts).filter(Shifts.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Check user has access
    if not check_store_access(db, current_user, shift.store_id):
        raise HTTPException(status_code=403, detail="No access to this store")

    update_data = payload.model_dump(exclude_unset=True)

    # Run compliance checks only when times or employee change
    violations: list[str] = []
    if any(k in update_data for k in ("start_datetime_utc", "end_datetime_utc", "employee_id")):
        new_start = (update_data.get("start_datetime_utc") or shift.start_datetime_utc).replace(tzinfo=None)
        new_end = (update_data.get("end_datetime_utc") or shift.end_datetime_utc).replace(tzinfo=None)
        new_employee_id = update_data.get("employee_id") or shift.employee_id
        existing = _load_scheduler_shifts(db, new_employee_id, new_start, exclude_shift_id=shift_id)
        violations = (
            check_min_rest(new_employee_id, new_start, new_end, existing)
            + check_rolling_window(new_employee_id, new_start.date(), existing)
        )

    for field, value in update_data.items():
        setattr(shift, field, value)

    db.commit()
    db.refresh(shift)
    response = ShiftWithViolationsResponse.model_validate(shift)
    response.violations = violations
    return response


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    shift = db.query(Shifts).filter(Shifts.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Check user has access
    if not check_store_access(db, current_user, shift.store_id):
        raise HTTPException(status_code=403, detail="No access to this store")

    db.delete(shift)
    db.commit()