from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AIInputBase(BaseModel):
    input_text: str
    context_tables: Optional[list] = None


class AIInputCreate(AIInputBase):
    """req_by_user_id is set from the authenticated user, not the payload"""
    store_id: Optional[int] = None  # explicit store context for admin requests
    as_preview: bool = False         # if True, process LLM but don't create AIProposal yet


class AIInputResponse(AIInputBase):
    id: int
    req_by_user_id: int
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True