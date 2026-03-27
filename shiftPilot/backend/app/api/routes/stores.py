from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin
from app.db.models.stores import Stores
from app.db.models.users import Users
from app.schemas.stores import StoreCreate, StoreUpdate, StoreResponse

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    existing = db.query(Stores).filter(Stores.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Store name already exists")

    store = Stores(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("", response_model=List[StoreResponse])
def list_stores(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return db.query(Stores).offset(skip).limit(limit).all()


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.put("/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: int,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    store = db.query(Stores).filter(Stores.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    db.delete(store)
    db.commit()