from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models.store_departments import StoreDepartment
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.users import Users
from app.schemas.store_departments import StoreDepartmentCreate, StoreDepartmentResponse

router = APIRouter(prefix="/store-departments", tags=["store-departments"])


@router.post("", response_model=StoreDepartmentResponse, status_code=status.HTTP_201_CREATED)
def add_department_to_store(
    payload: StoreDepartmentCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # Validate store exists
    store = db.query(Stores).filter(Stores.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Validate department exists
    department = db.query(Departments).filter(Departments.id == payload.department_id).first()
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
    current_user: Users = Depends(get_current_user),
):
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return db.query(StoreDepartment).filter(StoreDepartment.store_id == store_id).all()


@router.delete("/store/{store_id}/department/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_department_from_store(
    store_id: int,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    link = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == store_id,
        StoreDepartment.department_id == department_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Store-department link not found")

    db.delete(link)
    db.commit()