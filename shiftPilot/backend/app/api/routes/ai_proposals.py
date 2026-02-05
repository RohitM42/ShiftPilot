from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin, is_manager_or_admin, is_admin, user_owns_proposal
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs
from app.db.models.ai_proposals import AIProposals, ProposalStatus, ProposalType
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.ai_proposals import AIProposalCreate, AIProposalUpdate, AIProposalResponse

router = APIRouter(prefix="/ai-proposals", tags=["ai-proposals"])


@router.post("", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def create_ai_proposal(
    payload: AIProposalCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create AI proposal - any authenticated user"""
    output = db.query(AIOutputs).filter(AIOutputs.id == payload.ai_output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="AI output not found")
    
    proposal = AIProposals(
        ai_output_id=payload.ai_output_id,
        type=payload.type,
        store_id=payload.store_id,
        department_id=payload.department_id,
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
    """Approve proposal - manager (AVAILABILITY only) or admin (any type)"""
    proposal = db.query(AIProposals).filter(AIProposals.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Proposal is not pending")
    
    # Check permission based on proposal type
    if proposal.type != ProposalType.AVAILABILITY and not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required for this proposal type")
    
    proposal.status = ProposalStatus.APPROVED
    proposal.last_actioned_by = current_user.id
    
    # TODO: Apply the actual changes to the relevant table (availability, coverage, etc.)
    
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