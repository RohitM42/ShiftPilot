from pydantic import BaseModel
from datetime import time, datetime
from typing import Optional
from app.db.models.availability_rules import AvailabilityRuleType


class AvailabilityRuleBase(BaseModel):
    employee_id: int
    day_of_week: int  # 0-6
    start_time_local: Optional[time] = None
    end_time_local: Optional[time] = None
    rule_type: AvailabilityRuleType
    priority: int = 3
    active: bool = True


class AvailabilityRuleCreate(AvailabilityRuleBase):
    pass


class AvailabilityRuleUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time_local: Optional[time] = None
    end_time_local: Optional[time] = None
    rule_type: Optional[AvailabilityRuleType] = None
    priority: Optional[int] = None
    active: Optional[bool] = None


class AvailabilityRuleResponse(AvailabilityRuleBase):
    id: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True