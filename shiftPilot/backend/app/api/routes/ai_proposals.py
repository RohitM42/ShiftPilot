from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin, is_manager_or_admin, is_admin, user_owns_proposal
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs
from app.db.models.ai_proposals import AIProposals, ProposalStatus, ProposalType, ProposalSource
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.ai_proposals import (
    AIProposalCreate,
    AIProposalUpdate,
    AIProposalResponse,
    ManualAvailabilityProposalCreate,
    ManualSchedulingProposalCreate,
)
from app.services.ai import apply_proposal, ApprovalError


router = APIRouter(prefix="/ai-proposals", tags=["ai-proposals"])


@router.post("", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def create_ai_proposal(
    payload: AIProposalCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create AI proposal - any authenticated user"""
    if payload.ai_output_id:
        output = db.query(AIOutputs).filter(AIOutputs.id == payload.ai_output_id).first()
        if not output:
            raise HTTPException(status_code=404, detail="AI output not found")

    proposal = AIProposals(
        ai_output_id=payload.ai_output_id,
        source=payload.source,
        changes_json=payload.changes_json,
        type=payload.type,
        store_id=payload.store_id,
        department_id=payload.department_id,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/from-output/{output_id}", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def confirm_preview_proposal(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Convert a preview AIOutput into a real PENDING AIProposal.
    Only the user who generated the output (or a manager/admin) can confirm it.
    Fails if a proposal already exists for this output.
    """
    output = db.query(AIOutputs).filter(AIOutputs.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="AI output not found")

    # Ownership check
    ai_input = db.query(AIInputs).filter(AIInputs.id == output.input_id).first()
    if not ai_input:
        raise HTTPException(status_code=404, detail="AI input not found")
    if ai_input.req_by_user_id != current_user.id and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to confirm this proposal")

    # Guard against double-confirm
    existing = db.query(AIProposals).filter(AIProposals.ai_output_id == output_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="A proposal already exists for this output")

    result = output.result_json or {}
    intent_type = result.get("intent_type")
    type_map = {
        "AVAILABILITY": ProposalType.AVAILABILITY,
        "COVERAGE": ProposalType.COVERAGE,
        "ROLE_REQUIREMENT": ProposalType.ROLE_REQUIREMENT,
    }
    proposal_type = type_map.get(intent_type)
    if not proposal_type:
        raise HTTPException(status_code=422, detail=f"Cannot create proposal for intent type: {intent_type}")

    # AVAILABILITY results don't include store_id in the schema — derive from employee
    from app.db.models.employees import Employees
    resolved_store_id = result.get("store_id")
    if resolved_store_id is None:
        emp_user_id = output.affects_user_id or ai_input.req_by_user_id
        emp = db.query(Employees).filter(Employees.user_id == emp_user_id).first()
        if emp:
            resolved_store_id = emp.store_id

    proposal = AIProposals(
        ai_output_id=output_id,
        source=ProposalSource.AI,
        type=proposal_type,
        store_id=resolved_store_id,
        department_id=result.get("department_id"),
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("/pending", response_model=List[AIProposalResponse])
def list_pending_proposals(
    type: Optional[ProposalType] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List all pending proposals - manager/admin only"""
    query = db.query(AIProposals).filter(AIProposals.status == ProposalStatus.PENDING)
    
    if type:
        query = query.filter(AIProposals.type == type)
    
    return query.order_by(AIProposals.created_at.asc()).offset(skip).limit(limit).all()


@router.get("/pending/store/{store_id}", response_model=List[AIProposalResponse])
def list_pending_proposals_by_store(
    store_id: int,
    type: Optional[ProposalType] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List pending proposals for a store - manager/admin only"""
    query = db.query(AIProposals).filter(
        AIProposals.status == ProposalStatus.PENDING,
        AIProposals.store_id == store_id
    )
    
    if type:
        query = query.filter(AIProposals.type == type)
    
    return query.order_by(AIProposals.created_at.asc()).offset(skip).limit(limit).all()


@router.get("/store/{store_id}", response_model=List[AIProposalResponse])
def list_proposals_by_store(
    store_id: int,
    status_filter: Optional[ProposalStatus] = Query(None, alias="status"),
    type: Optional[ProposalType] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List all proposals for a store (any status) - manager/admin only"""
    query = db.query(AIProposals).filter(AIProposals.store_id == store_id)

    if status_filter:
        query = query.filter(AIProposals.status == status_filter)
    if type:
        query = query.filter(AIProposals.type == type)

    return query.order_by(AIProposals.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/all", response_model=List[AIProposalResponse])
def list_all_proposals(
    status_filter: Optional[ProposalStatus] = Query(None, alias="status"),
    type: Optional[ProposalType] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List all proposals (any status, any store) - manager/admin only"""
    query = db.query(AIProposals)

    if status_filter:
        query = query.filter(AIProposals.status == status_filter)
    if type:
        query = query.filter(AIProposals.type == type)

    return query.order_by(AIProposals.created_at.desc()).offset(skip).limit(limit).all()



@router.post("/propose/manual", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def create_manual_availability_proposal(
    payload: ManualAvailabilityProposalCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create a manual availability proposal without going through the LLM - any authenticated user"""
    from app.db.models.employees import Employees
    employee = db.query(Employees).filter(Employees.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee record not found")

    changes_json = {
        "intent_type": "AVAILABILITY",
        "employee_id": employee.id,
        "summary": payload.summary,
        "changes": [c.model_dump() for c in payload.changes],
    }

    proposal = AIProposals(
        ai_output_id=None,
        source=ProposalSource.MANUAL,
        changes_json=changes_json,
        type=ProposalType.AVAILABILITY,
        store_id=employee.store_id,
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/propose/manual/scheduling", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def create_manual_scheduling_proposal(
    payload: ManualSchedulingProposalCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """Create a manual coverage or role requirement proposal — manager/admin only"""
    if payload.intent_type not in ("COVERAGE", "ROLE_REQUIREMENT"):
        raise HTTPException(status_code=400, detail="intent_type must be COVERAGE or ROLE_REQUIREMENT")

    proposal_type = ProposalType.COVERAGE if payload.intent_type == "COVERAGE" else ProposalType.ROLE_REQUIREMENT

    changes_json = {
        "intent_type": payload.intent_type,
        "store_id": payload.store_id,
        "department_id": payload.department_id,
        "summary": payload.summary,
        "changes": [c.model_dump() for c in payload.changes],
    }

    proposal = AIProposals(
        ai_output_id=None,
        source=ProposalSource.MANUAL,
        changes_json=changes_json,
        type=proposal_type,
        store_id=payload.store_id,
        department_id=payload.department_id,
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("/user/{user_id}", response_model=List[AIProposalResponse])
def list_proposals_by_affected_user(
    user_id: int,
    status_filter: Optional[ProposalStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List proposals affecting a user - manager/admin only"""
    output_ids = db.query(AIOutputs.id).filter(
        AIOutputs.affects_user_id == user_id
    ).subquery()
    
    query = db.query(AIProposals).filter(AIProposals.ai_output_id.in_(output_ids))
    
    if status_filter:
        query = query.filter(AIProposals.status == status_filter)
    
    return query.order_by(AIProposals.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{proposal_id}", response_model=AIProposalResponse)
def get_ai_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get single AI proposal - self or manager/admin"""
    proposal = db.query(AIProposals).filter(AIProposals.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    
    if not user_owns_proposal(db, current_user, proposal) and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to view this proposal")
    
    return proposal


@router.patch("/{proposal_id}/approve", response_model=AIProposalResponse)
def approve_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """Approve proposal and apply changes - manager (AVAILABILITY only) or admin (any type)"""
    proposal = db.query(AIProposals).filter(AIProposals.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Proposal is not pending")
    
    # Check permission based on proposal type
    if proposal.type != ProposalType.AVAILABILITY and not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required for this proposal type")
    
    # Apply the changes to constraint tables
    try:
        apply_proposal(db, proposal, current_user.id)
    except ApprovalError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    proposal.status = ProposalStatus.APPROVED
    proposal.last_actioned_by = current_user.id
    
    db.commit()
    db.refresh(proposal)
    return proposal


@router.patch("/{proposal_id}/reject", response_model=AIProposalResponse)
def reject_proposal(
    proposal_id: int,
    rejection_reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """Reject proposal - manager (AVAILABILITY only) or admin (any type)"""
    proposal = db.query(AIProposals).filter(AIProposals.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Proposal is not pending")
    
    # Check permission based on proposal type
    if proposal.type != ProposalType.AVAILABILITY and not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required for this proposal type")
    
    proposal.status = ProposalStatus.REJECTED
    proposal.rejection_reason = rejection_reason
    proposal.last_actioned_by = current_user.id
    
    db.commit()
    db.refresh(proposal)
    return proposal


@router.patch("/{proposal_id}/cancel", response_model=AIProposalResponse)
def cancel_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Cancel proposal - self (pending only) or admin"""
    proposal = db.query(AIProposals).filter(AIProposals.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Proposal is not pending")
    
    is_own = user_owns_proposal(db, current_user, proposal)
    if not is_own and not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to cancel this proposal")
    
    proposal.status = ProposalStatus.CANCELLED
    proposal.last_actioned_by = current_user.id
    
    db.commit()
    db.refresh(proposal)
    return proposal