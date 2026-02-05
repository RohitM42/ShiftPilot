# app/api/routes/me.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_db, get_current_user, get_current_employee
from app.db.models.users import Users
from app.db.models.employees import Employees
from app.db.models.shifts import Shifts
from app.db.models.availability_rules import AvailabilityRules
from app.db.models.time_off_requests import TimeOffRequests
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs, AIOutputStatus
from app.db.models.ai_proposals import AIProposals, ProposalStatus
from app.schemas.shifts import ShiftResponse
from app.schemas.availability_rules import AvailabilityRuleResponse
from app.schemas.time_off_requests import TimeOffRequestResponse
from app.schemas.employee_departments import EmployeeDepartmentResponse
from app.schemas.employees import EmployeeResponse
from app.schemas.ai_inputs import AIInputResponse
from app.schemas.ai_outputs import AIOutputResponse
from app.schemas.ai_proposals import AIProposalResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/employee", response_model=EmployeeResponse)
def get_my_employee_record(
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's employee record"""
    return employee


@router.get("/shifts", response_model=List[ShiftResponse])
def get_my_shifts(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's shifts"""
    query = db.query(Shifts).filter(Shifts.employee_id == employee.id)
    
    if start_date:
        query = query.filter(Shifts.start_datetime_utc >= start_date)
    if end_date:
        query = query.filter(Shifts.end_datetime_utc <= end_date)
    
    return query.order_by(Shifts.start_datetime_utc).all()


@router.get("/availability-rules", response_model=List[AvailabilityRuleResponse])
def get_my_availability_rules(
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's availability rules"""
    return db.query(AvailabilityRules).filter(AvailabilityRules.employee_id == employee.id).all()


@router.get("/time-off-requests", response_model=List[TimeOffRequestResponse])
def get_my_time_off_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get current user's time off requests"""
    query = db.query(TimeOffRequests).filter(TimeOffRequests.employee_id == employee.id)
    
    if status:
        query = query.filter(TimeOffRequests.status == status)
    
    return query.order_by(TimeOffRequests.start_date.desc()).all()


@router.get("/departments", response_model=List[EmployeeDepartmentResponse])
def get_my_departments(
    db: Session = Depends(get_db),
    employee: Employees = Depends(get_current_employee),
):
    """Get departments current user is assigned to"""
    return db.query(EmployeeDepartments).filter(EmployeeDepartments.employee_id == employee.id).all()


# AI Inputs
@router.get("/ai-inputs", response_model=List[AIInputResponse])
def get_my_ai_inputs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get current user's AI inputs"""
    return db.query(AIInputs).filter(
        AIInputs.req_by_user_id == current_user.id
    ).order_by(AIInputs.created_at.desc()).offset(skip).limit(limit).all()


# AI Outputs
@router.get("/ai-outputs", response_model=List[AIOutputResponse])
def get_my_ai_outputs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get AI outputs affecting current user or from their inputs"""
    my_input_ids = db.query(AIInputs.id).filter(
        AIInputs.req_by_user_id == current_user.id
    ).subquery()
    
    return db.query(AIOutputs).filter(
        (AIOutputs.affects_user_id == current_user.id) | 
        (AIOutputs.input_id.in_(my_input_ids))
    ).order_by(AIOutputs.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/ai-outputs/pending-clarification", response_model=List[AIOutputResponse])
def get_my_pending_clarification(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get current user's outputs needing clarification"""
    my_input_ids = db.query(AIInputs.id).filter(
        AIInputs.req_by_user_id == current_user.id
    ).subquery()
    
    return db.query(AIOutputs).filter(
        AIOutputs.status == AIOutputStatus.NEEDS_CLARIFICATION,
        (AIOutputs.affects_user_id == current_user.id) | 
        (AIOutputs.input_id.in_(my_input_ids))
    ).order_by(AIOutputs.created_at.asc()).all()


# AI Proposals
@router.get("/ai-proposals", response_model=List[AIProposalResponse])
def get_my_ai_proposals(
    status_filter: Optional[ProposalStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get current user's AI proposals"""
    my_input_ids = db.query(AIInputs.id).filter(
        AIInputs.req_by_user_id == current_user.id
    ).subquery()
    
    my_output_ids = db.query(AIOutputs.id).filter(
        (AIOutputs.affects_user_id == current_user.id) | 
        (AIOutputs.input_id.in_(my_input_ids))
    ).subquery()
    
    query = db.query(AIProposals).filter(AIProposals.ai_output_id.in_(my_output_ids))
    
    if status_filter:
        query = query.filter(AIProposals.status == status_filter)
    
    return query.order_by(AIProposals.created_at.desc()).offset(skip).limit(limit).all()