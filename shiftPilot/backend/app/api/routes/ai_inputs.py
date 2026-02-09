from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin, require_manager_or_admin, is_manager_or_admin
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputStatus
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.ai_inputs import AIInputCreate, AIInputResponse
from app.schemas.ai_outputs import AIOutputResponse
from app.services.ai import process_ai_input

router = APIRouter(prefix="/ai-inputs", tags=["ai-inputs"])


@router.post("", response_model=AIOutputResponse, status_code=status.HTTP_201_CREATED)
def create_ai_input(
    payload: AIInputCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create AI input and process it through the AI service.
    Returns the AI output (which contains the parsed intent and proposal reference).
    """
    ai_input = AIInputs(
        req_by_user_id=current_user.id,
        input_text=payload.input_text,
        context_tables=payload.context_tables,
    )
    db.add(ai_input)
    db.flush()  # get id before processing

    try:
        ai_output = process_ai_input(db, ai_input, current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI processing failed: {str(e)}",
        )

    return ai_output


@router.get("/unprocessed", response_model=List[AIInputResponse])
def list_unprocessed_inputs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    """List unprocessed inputs - admin only (system monitoring)"""
    return db.query(AIInputs).filter(
        AIInputs.processed == False
    ).order_by(AIInputs.created_at.asc()).offset(skip).limit(limit).all()


@router.get("/{input_id}", response_model=AIInputResponse)
def get_ai_input(
    input_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get single AI input - self or manager/admin"""
    ai_input = db.query(AIInputs).filter(AIInputs.id == input_id).first()
    if not ai_input:
        raise HTTPException(status_code=404, detail="AI input not found")
    
    is_own = ai_input.req_by_user_id == current_user.id
    if not is_own and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to view this input")
    
    return ai_input


@router.get("/user/{user_id}", response_model=List[AIInputResponse])
def list_ai_inputs_by_user(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    """List AI inputs by user - manager/admin only"""
    return db.query(AIInputs).filter(
        AIInputs.req_by_user_id == user_id
    ).order_by(AIInputs.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/{input_id}/processed", response_model=AIInputResponse)
def mark_input_processed(
    input_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_admin),
):
    """Mark input as processed - admin only (internal use)"""
    ai_input = db.query(AIInputs).filter(AIInputs.id == input_id).first()
    if not ai_input:
        raise HTTPException(status_code=404, detail="AI input not found")
    
    ai_input.processed = True
    db.commit()
    db.refresh(ai_input)
    return ai_input