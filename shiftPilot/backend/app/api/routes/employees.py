from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin, require_admin
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.db.models.stores import Stores
from app.schemas.employees import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    # Validate user exists
    user = db.query(Users).filter(Users.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate store exists
    store = db.query(Stores).filter(Stores.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Check if user already has employee record
    existing = db.query(Employees).filter(Employees.user_id == payload.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has an employee record")

    employee = Employees(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    store_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    query = db.query(Employees)
    if store_id:
        query = query.filter(Employees.store_id == store_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    employee = db.query(Employees).filter(Employees.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    employee = db.query(Employees).filter(Employees.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Validate store if being updated
    if "store_id" in update_data:
        store = db.query(Stores).filter(Stores.id == update_data["store_id"]).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    employee = db.query(Employees).filter(Employees.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(employee)
    db.commit()