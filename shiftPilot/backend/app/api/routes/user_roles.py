from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin
from app.db.models.user_roles import UserRoles
from app.db.models.users import Users
from app.db.models.stores import Stores
from app.schemas.user_roles import UserRoleCreate, UserRoleUpdate, UserRoleResponse

router = APIRouter(prefix="/user-roles", tags=["user-roles"])


@router.post("", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
def create_user_role(
    payload: UserRoleCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.store_id:
        store = db.query(Stores).filter(Stores.id == payload.store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

    existing = db.query(UserRoles).filter(
        UserRoles.user_id == payload.user_id,
        UserRoles.store_id == payload.store_id,
        UserRoles.role == payload.role
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")

    role = UserRoles(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/user/{user_id}", response_model=List[UserRoleResponse])
def get_roles_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return db.query(UserRoles).filter(UserRoles.user_id == user_id).all()


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    role = db.query(UserRoles).filter(UserRoles.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(role)
    db.commit()