from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin, require_admin
from app.db.models.labour_budgets import LabourBudgets
from app.db.models.store_departments import StoreDepartment
from app.db.models.users import Users
from app.schemas.labour_budgets import LabourBudgetCreate, LabourBudgetUpdate, LabourBudgetResponse

router = APIRouter(prefix="/labour-budgets", tags=["labour-budgets"])


@router.post("", response_model=LabourBudgetResponse, status_code=status.HTTP_201_CREATED)
def create_labour_budget(
    payload: LabourBudgetCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    store_dept = db.query(StoreDepartment).filter(
        StoreDepartment.store_id == payload.store_id,
        StoreDepartment.department_id == payload.department_id
    ).first()
    if not store_dept:
        raise HTTPException(status_code=404, detail="Store-department combination not found")

    existing = db.query(LabourBudgets).filter(
        LabourBudgets.store_id == payload.store_id,
        LabourBudgets.department_id == payload.department_id,
        LabourBudgets.week_start_date == payload.week_start_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Budget already exists for this week")

    budget = LabourBudgets(**payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("", response_model=List[LabourBudgetResponse])
def list_labour_budgets(
    store_id: Optional[int] = None,
    department_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    query = db.query(LabourBudgets)
    if store_id:
        query = query.filter(LabourBudgets.store_id == store_id)
    if department_id:
        query = query.filter(LabourBudgets.department_id == department_id)

    return query.offset(skip).limit(limit).all()


@router.get("/{budget_id}", response_model=LabourBudgetResponse)
def get_labour_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    budget = db.query(LabourBudgets).filter(LabourBudgets.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Labour budget not found")
    return budget


@router.put("/{budget_id}", response_model=LabourBudgetResponse)
def update_labour_budget(
    budget_id: int,
    payload: LabourBudgetUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    budget = db.query(LabourBudgets).filter(LabourBudgets.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Labour budget not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(budget, field, value)

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labour_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    budget = db.query(LabourBudgets).filter(LabourBudgets.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Labour budget not found")

    db.delete(budget)
    db.commit()