from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models.availability_rules import AvailabilityRules
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.schemas.availability_rules import AvailabilityRuleCreate, AvailabilityRuleUpdate, AvailabilityRuleResponse

router = APIRouter(prefix="/availability-rules", tags=["availability-rules"])


@router.post("", response_model=AvailabilityRuleResponse, status_code=status.HTTP_201_CREATED)
def create_availability_rule(
    payload: AvailabilityRuleCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    rule = AvailabilityRules(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/employee/{employee_id}", response_model=List[AvailabilityRuleResponse])
def get_availability_for_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    employee = db.query(Employees).filter(Employees.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return db.query(AvailabilityRules).filter(AvailabilityRules.employee_id == employee_id).all()


@router.put("/{rule_id}", response_model=AvailabilityRuleResponse)
def update_availability_rule(
    rule_id: int,
    payload: AvailabilityRuleUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    rule = db.query(AvailabilityRules).filter(AvailabilityRules.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Availability rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    rule = db.query(AvailabilityRules).filter(AvailabilityRules.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Availability rule not found")

    db.delete(rule)
    db.commit()