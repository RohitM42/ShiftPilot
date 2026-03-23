from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin
from app.db.models.role_requirements import RoleRequirements
from app.db.models.stores import Stores
from app.db.models.users import Users
from app.schemas.role_requirements import RoleRequirementCreate, RoleRequirementUpdate, RoleRequirementResponse

router = APIRouter(prefix="/role-requirements", tags=["role-requirements"])


@router.post("", response_model=RoleRequirementResponse, status_code=status.HTTP_201_CREATED)
def create_role_requirement(
    payload: RoleRequirementCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    store = db.query(Stores).filter(Stores.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    requirement = RoleRequirements(**payload.model_dump(), last_modified_by_user_id=current_user.id)
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.get("", response_model=List[RoleRequirementResponse])
def list_role_requirements(
    store_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    query = db.query(RoleRequirements)
    if store_id:
        query = query.filter(RoleRequirements.store_id == store_id)

    return query.offset(skip).limit(limit).all()


@router.get("/{requirement_id}", response_model=RoleRequirementResponse)
def get_role_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(RoleRequirements).filter(RoleRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Role requirement not found")
    return requirement


@router.put("/{requirement_id}", response_model=RoleRequirementResponse)
def update_role_requirement(
    requirement_id: int,
    payload: RoleRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(RoleRequirements).filter(RoleRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Role requirement not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(requirement, field, value)

    requirement.last_modified_by_user_id = current_user.id
    db.commit()
    db.refresh(requirement)
    return requirement


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    requirement = db.query(RoleRequirements).filter(RoleRequirements.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Role requirement not found")

    db.delete(requirement)
    db.commit()