from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_manager_or_admin, is_manager_or_admin
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs, AIOutputStatus
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.ai_outputs import AIOutputCreate, AIOutputUpdate, AIOutputResponse

router = APIRouter(prefix="/ai-outputs", tags=["ai-outputs"])


def user_owns_output(db: Session, user: Users, output: AIOutputs) -> bool:
    """Check if user owns the output (via input or affects_user_id)"""
    if output.affects_user_id == user.id:
        return True
    ai_input = db.query(AIInputs).filter(AIInputs.id == output.input_id).first()
    return ai_input and ai_input.req_by_user_id == user.id


@router.get("/pending-clarification", response_model=List[AIOutputResponse])
def list_pending_clarification(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List outputs needing clarification - manager/admin only"""
    return db.query(AIOutputs).filter(
        AIOutputs.status == AIOutputStatus.NEEDS_CLARIFICATION
    ).order_by(AIOutputs.created_at.asc()).offset(skip).limit(limit).all()


@router.get("/input/{input_id}", response_model=AIOutputResponse)
def get_output_by_input(
    input_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get output for a given input - self or manager/admin"""
    ai_input = db.query(AIInputs).filter(AIInputs.id == input_id).first()
    if not ai_input:
        raise HTTPException(status_code=404, detail="AI input not found")
    
    is_own = ai_input.req_by_user_id == current_user.id
    if not is_own and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to view this output")
    
    output = db.query(AIOutputs).filter(AIOutputs.input_id == input_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="AI output not found for this input")
    
    return output


@router.get("/user/{user_id}", response_model=List[AIOutputResponse])
def list_outputs_by_affected_user(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List outputs affecting a user - manager/admin only"""
    return db.query(AIOutputs).filter(
        AIOutputs.affects_user_id == user_id
    ).order_by(AIOutputs.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{output_id}", response_model=AIOutputResponse)
def get_ai_output(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get single AI output - self or manager/admin"""
    output = db.query(AIOutputs).filter(AIOutputs.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="AI output not found")
    
    if not user_owns_output(db, current_user, output) and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to view this output")
    
    return output


@router.patch("/{output_id}", response_model=AIOutputResponse)
def update_ai_output(
    output_id: int,
    payload: AIOutputUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Update AI output (resolve clarification) - self or manager/admin"""
    output = db.query(AIOutputs).filter(AIOutputs.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="AI output not found")
    
    if not user_owns_output(db, current_user, output) and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to update this output")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(output, field, value)
    
    db.commit()
    db.refresh(output)
    return output