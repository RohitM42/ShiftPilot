from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.db.models.ai_proposals import ProposalType, ProposalStatus, ProposalSource


class ManualAvailabilityChange(BaseModel):
    action: str                       # ADD | REMOVE | UPDATE
    day_of_week: int                  # 0-6
    start_time: Optional[str] = None  # HH:MM or null (all day)
    end_time: Optional[str] = None
    rule_type: str                    # AVAILABLE | UNAVAILABLE | PREFERRED


class ManualAvailabilityProposalCreate(BaseModel):
    changes: List[ManualAvailabilityChange]
    summary: str


class ManualSchedulingChange(BaseModel):
    action: str                              # ADD
    day_of_week: Optional[int] = None        # 0-6, or null = every day (role requirements)
    start_time: str                          # HH:MM
    end_time: str                            # HH:MM
    # Coverage fields
    min_staff: Optional[int] = None
    max_staff: Optional[int] = None
    # Role requirement fields
    requires_manager: Optional[bool] = None
    requires_keyholder: Optional[bool] = None
    min_manager_count: Optional[int] = None


class ManualSchedulingProposalCreate(BaseModel):
    intent_type: str                         # COVERAGE or ROLE_REQUIREMENT
    store_id: int
    department_id: Optional[int] = None      # required for COVERAGE, optional for ROLE_REQUIREMENT
    summary: str
    changes: List[ManualSchedulingChange]


class AIProposalBase(BaseModel):
    type: ProposalType
    store_id: Optional[int] = None
    department_id: Optional[int] = None


class AIProposalCreate(AIProposalBase):
    ai_output_id: Optional[int] = None
    source: ProposalSource = ProposalSource.AI
    changes_json: Optional[dict] = None


class AIProposalUpdate(BaseModel):
    status: Optional[ProposalStatus] = None
    rejection_reason: Optional[str] = None
    last_actioned_by: Optional[int] = None


class AIProposalResponse(AIProposalBase):
    id: int
    ai_output_id: Optional[int]
    source: ProposalSource
    changes_json: Optional[dict]
    status: ProposalStatus
    rejection_reason: Optional[str]
    last_actioned_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True