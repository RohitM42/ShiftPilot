from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin, require_manager_or_admin
from app.core.security import get_password_hash
from app.db.models.users import Users
from app.db.models.employees import Employees
from app.db.models.user_roles import UserRoles, Role
from app.schemas.users import UserCreate, UserUpdate, UserResponse, UserPasswordReset

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    existing = db.query(Users).filter(Users.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = Users(
        email=payload.email,
        firstname=payload.firstname,
        surname=payload.surname,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Users = Depends(get_current_user)):
    return current_user


@router.get("/unassigned", response_model=List[UserResponse])
def list_unassigned_users(
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """Users with no employee record and no ADMIN role — eligible to become employees."""
    has_employee = db.query(Employees.user_id).subquery()
    has_admin_role = db.query(UserRoles.user_id).filter(UserRoles.role == Role.ADMIN).subquery()
    return (
        db.query(Users)
        .filter(Users.id.notin_(has_employee))
        .filter(Users.id.notin_(has_admin_role))
        .all()
    )


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    store_id: Optional[int] = Query(default=None),
    unassigned: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    query = db.query(Users)
    if store_id is not None:
        query = (
            query.join(UserRoles, UserRoles.user_id == Users.id)
            .filter(UserRoles.store_id == store_id)
            .distinct()
        )
    elif unassigned:
        has_store_role = db.query(UserRoles.user_id).filter(UserRoles.store_id.isnot(None)).subquery()
        query = query.filter(Users.id.notin_(has_store_role))
    return query.offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()