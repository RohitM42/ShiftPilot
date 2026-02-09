from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.store_departments import StoreDepartment
from app.db.models.users import Users
from app.schemas.coverage_requirements import CoverageRequirementCreate, CoverageRequirementUpdate, CoverageRequirementResponse

router = APIRouter(prefix="/coverage-requirements", tags=["coverage-requirements"])


@router.post("", response_model=CoverageRequirementResponse, status_code=status.HTTP_201_CREATED)
def create_coverage_requirement(
    payload: CoverageRequirementCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    store_dept = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == payload.store_id,
        StoreDepartment.department_id == payload.department_id
    ).first()
    if not store_dept:
        raise HTTPException(status_code=404, detail="Store-department combination not found")

    requirement = CoverageRequirements(**payload.model_dump(), last_modified_by_user_id=current_user.id)
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.get("", response_model=List[CoverageRequirementResponse])
def list_coverage_requirements(
    store_id: Optional[int] = None,
    department_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    query = db.query(CoverageRequirements)
    if store_id:
        query = query.filter(CoverageRequirements.store_id == store_id)
    if department_id:
        query = query.filter(CoverageRequirements.department_id == department_id)

    return query.offset(skip).limit(limit).all()


@router.get("/{requirement_id}", response_model=CoverageRequirementResponse)
def get_coverage_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(CoverageRequirements).filter(CoverageRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Coverage requirement not found")
    return requirement


@router.put("/{requirement_id}", response_model=CoverageRequirementResponse)
def update_coverage_requirement(
    requirement_id: int,
    payload: CoverageRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(CoverageRequirements).filter(CoverageRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Coverage requirement not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(requirement, field, value)

    requirement.last_modified_by_user_id = current_user.id
    db.commit()
    db.refresh(requirement)
    return requirement


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coverage_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(CoverageRequirements).filter(CoverageRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Coverage requirement not found")

    db.delete(requirement)
    db.commit()