from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AIInputBase(BaseModel):
    input_text: str
    context_tables: Optional[list] = None


class AIInputCreate(AIInputBase):
    """req_by_user_id is set from the authenticated user, not the payload"""
    pass


class AIInputResponse(AIInputBase):
    id: int
    req_by_user_id: int
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True