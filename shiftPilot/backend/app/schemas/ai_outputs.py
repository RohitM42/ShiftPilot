from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.models.ai_outputs import AIOutputStatus


class AIOutputBase(BaseModel):
    result_json: dict
    summary: str
    status: AIOutputStatus = AIOutputStatus.COMPLETE
    model_used: Optional[str] = None
    affects_user_id: Optional[int] = None


class AIOutputCreate(AIOutputBase):
    input_id: int


class AIOutputUpdate(BaseModel):
    result_json: Optional[dict] = None
    status: Optional[AIOutputStatus] = None
    affects_user_id: Optional[int] = None


class AIOutputResponse(AIOutputBase):
    id: int
    input_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True