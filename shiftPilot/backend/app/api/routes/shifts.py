from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_db, get_current_user, require_manager_or_admin, check_store_access, get_accessible_store_ids
from app.db.models.shifts import Shifts
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.shifts import ShiftCreate, ShiftUpdate, ShiftResponse

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
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

    department = db.query(Departments).filter(Departments.id == payload.department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    shift = Shifts(**payload.model_dump(), created_by_user_id=current_user.id)
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


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


@router.put("/{shift_id}", response_model=ShiftResponse)
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
    for field, value in update_data.items():
        setattr(shift, field, value)

    db.commit()
    db.refresh(shift)
    return shift


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