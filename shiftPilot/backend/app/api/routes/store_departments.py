from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin, require_manager_or_admin
from app.db.models.store_departments import StoreDepartment
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.users import Users
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.employees import Employees, EmploymentStatus
from app.db.models.employee_departments import EmployeeDepartments
from app.schemas.store_departments import StoreDepartmentCreate, StoreDepartmentResponse

router = APIRouter(prefix="/store-departments", tags=["store-departments"])


@router.post("", response_model=StoreDepartmentResponse, status_code=status.HTTP_201_CREATED)
def add_department_to_store(
    payload: StoreDepartmentCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    # Validate store exists
    store = db.query(Stores).filter(Stores.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Validate department exists
    department = db.query(Departments).filter(
        Departments.id == payload.department_id,
        Departments.active == True
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check if already linked
    existing = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == payload.store_id,
        StoreDepartment.department_id == payload.department_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department already linked to store")

    link = StoreDepartment(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/store/{store_id}", response_model=List[StoreDepartmentResponse])
def get_departments_for_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return db.query(StoreDepartment).filter(StoreDepartment.store_id == store_id).all()


@router.delete("/store/{store_id}/department/{department_id}", status_code=status.HTTP_200_OK)
def remove_department_from_store(
    store_id: int,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    link = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == store_id,
        StoreDepartment.department_id == department_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Store-department link not found")

    # Soft-delete active coverage requirements for this store+dept
    db.query(CoverageRequirements).filter(
        CoverageRequirements.store_id == store_id,
        CoverageRequirements.department_id == department_id,
        CoverageRequirements.active == True
    ).update({"active": False})

    # Handle employees at this store whose primary is this dept
    # Only active employees (not LEAVER)
    primary_links_with_employees = (
        db.query(EmployeeDepartments, Employees)
        .join(Employees, Employees.id == EmployeeDepartments.employee_id)
        .filter(
            Employees.store_id == store_id,
            Employees.employment_status != EmploymentStatus.LEAVER,
            EmployeeDepartments.department_id == department_id,
            EmployeeDepartments.is_primary == True
        )
        .all()
    )

    warnings = []
    for primary_link, emp in primary_links_with_employees:
        other = db.query(EmployeeDepartments).filter(
            EmployeeDepartments.employee_id == emp.id,
            EmployeeDepartments.department_id != department_id
        ).order_by(EmployeeDepartments.department_id).first()

        if other:
            other.is_primary = True
            primary_link.is_primary = False
        else:
            primary_link.is_primary = False
            user = db.query(Users).filter(Users.id == emp.user_id).first()
            warnings.append({
                "employee_id": emp.id,
                "name": f"{user.firstname} {user.surname}" if user else f"Employee {emp.id}"
            })

    db.delete(link)
    db.commit()
    return {"warnings": warnings}