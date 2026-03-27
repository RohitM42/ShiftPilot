from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_manager_or_admin, get_accessible_store_ids
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.employees import Employees
from app.db.models.departments import Departments
from app.db.models.users import Users
from app.schemas.employee_departments import EmployeeDepartmentCreate, EmployeeDepartmentResponse

router = APIRouter(prefix="/employee-departments", tags=["employee-departments"])


@router.get("", response_model=List[EmployeeDepartmentResponse])
def list_employee_departments(
    store_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    accessible_stores = get_accessible_store_ids(db, current_user)
    if accessible_stores is not None:
        if store_id and store_id not in accessible_stores:
            raise HTTPException(status_code=403, detail="No access to this store")

    query = db.query(EmployeeDepartments).join(
        Employees, EmployeeDepartments.employee_id == Employees.id
    )
    if accessible_stores is not None:
        query = query.filter(Employees.store_id.in_(accessible_stores))
    if store_id:
        query = query.filter(Employees.store_id == store_id)
    return query.all()


@router.post("", response_model=EmployeeDepartmentResponse, status_code=status.HTTP_201_CREATED)
def add_department_to_employee(
    payload: EmployeeDepartmentCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    # Validate employee exists
    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Validate department exists
    department = db.query(Departments).filter(
        Departments.id == payload.department_id,
        Departments.active == True
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check if already linked
    existing = db.query(EmployeeDepartments).filter(
        EmployeeDepartments.employee_id == payload.employee_id,
        EmployeeDepartments.department_id == payload.department_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee already linked to department")

    # If setting as primary, unset other primaries for this employee
    if payload.is_primary:
        db.query(EmployeeDepartments).filter(
            EmployeeDepartments.employee_id == payload.employee_id,
            EmployeeDepartments.is_primary == True
        ).update({"is_primary": False})

    link = EmployeeDepartments(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/employee/{employee_id}", response_model=List[EmployeeDepartmentResponse])
def get_departments_for_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    employee = db.query(Employees).filter(Employees.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return db.query(EmployeeDepartments).filter(EmployeeDepartments.employee_id == employee_id).all()


@router.put("/employee/{employee_id}/department/{department_id}/set-primary", response_model=EmployeeDepartmentResponse)
def set_primary_department(
    employee_id: int,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    link = db.query(EmployeeDepartments).filter(
        EmployeeDepartments.employee_id == employee_id,
        EmployeeDepartments.department_id == department_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Employee-department link not found")

    # Unset other primaries
    db.query(EmployeeDepartments).filter(
        EmployeeDepartments.employee_id == employee_id,
        EmployeeDepartments.is_primary == True
    ).update({"is_primary": False})

    link.is_primary = True
    db.commit()
    db.refresh(link)
    return link


@router.delete("/employee/{employee_id}/department/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_department_from_employee(
    employee_id: int,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    link = db.query(EmployeeDepartments).filter(
        EmployeeDepartments.employee_id == employee_id,
        EmployeeDepartments.department_id == department_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Employee-department link not found")

    db.delete(link)
    db.commit()