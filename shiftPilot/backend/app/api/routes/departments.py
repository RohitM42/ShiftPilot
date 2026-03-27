import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin, require_manager_or_admin
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.departments import Departments
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.employees import Employees, EmploymentStatus
from app.db.models.user_roles import UserRoles, Role
from app.db.models.users import Users
from app.schemas.departments import DepartmentCreate, DepartmentUpdate, DepartmentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    existing = db.query(Departments).filter(
        (Departments.name == payload.name) | (Departments.code == payload.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department name or code already exists")

    department = Departments(**payload.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.get("", response_model=List[DepartmentResponse])
def list_departments(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # Non-admins cannot see inactive departments
    is_admin = db.query(UserRoles).filter(
        UserRoles.user_id == current_user.id,
        UserRoles.role == Role.ADMIN,
        UserRoles.store_id.is_(None)
    ).first() is not None
    if not is_admin:
        include_inactive = False

    q = db.query(Departments)
    if not include_inactive:
        q = q.filter(Departments.active == True)
    return q.offset(skip).limit(limit).all()


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    department = db.query(Departments).filter(
        Departments.id == department_id,
        Departments.active == True
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    department = db.query(Departments).filter(Departments.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_200_OK)
def deactivate_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    dept = db.query(Departments).filter(
        Departments.id == department_id,
        Departments.active == True
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    primary_links = (
        db.query(EmployeeDepartments)
        .join(Employees, Employees.id == EmployeeDepartments.employee_id)
        .filter(
            EmployeeDepartments.department_id == department_id,
            EmployeeDepartments.is_primary == True,
            Employees.employment_status != EmploymentStatus.LEAVER
        )
        .all()
    )

    # Soft-delete all coverage requirements for this department across all stores
    db.query(CoverageRequirements).filter(
        CoverageRequirements.department_id == department_id,
        CoverageRequirements.active == True
    ).update({"active": False})

    warnings = []
    for link in primary_links:
        other = db.query(EmployeeDepartments).filter(
            EmployeeDepartments.employee_id == link.employee_id,
            EmployeeDepartments.department_id != department_id
        ).order_by(EmployeeDepartments.department_id).first()

        if other:
            other.is_primary = True
            link.is_primary = False
        else:
            link.is_primary = False
            emp = db.query(Employees).filter(Employees.id == link.employee_id).first()
            if emp is None:
                logger.warning(
                    "Dangling EmployeeDepartments row for employee_id=%s — no Employees record found",
                    link.employee_id
                )
            user = db.query(Users).filter(Users.id == emp.user_id).first() if emp else None
            warnings.append({
                "employee_id": link.employee_id,
                "name": f"{user.firstname} {user.surname}" if user else f"Employee {link.employee_id}"
            })

    dept.active = False
    db.commit()
    return {"id": department_id, "warnings": warnings}