from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.models.ai_proposals import ProposalType, ProposalStatus


class AIProposalBase(BaseModel):
    type: ProposalType
    store_id: Optional[int] = None
    department_id: Optional[int] = None


class AIProposalCreate(AIProposalBase):
    ai_output_id: int


class AIProposalUpdate(BaseModel):
    status: Optional[ProposalStatus] = None
    rejection_reason: Optional[str] = None
    last_actioned_by: Optional[int] = None


class AIProposalResponse(AIProposalBase):
    id: int
    ai_output_id: int
    status: ProposalStatus
    rejection_reason: Optional[str]
    last_actioned_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True