from pydantic import BaseModel
from datetime import time, datetime
from typing import Optional


class CoverageRequirementBase(BaseModel):
    store_id: int
    department_id: int
    day_of_week: int  # 0-6
    start_time_local: Optional[time] = None
    end_time_local: Optional[time] = None
    min_staff: int = 1
    max_staff: Optional[int] = None
    active: bool = True


class CoverageRequirementCreate(CoverageRequirementBase):
    pass


class CoverageRequirementUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time_local: Optional[time] = None
    end_time_local: Optional[time] = None
    min_staff: Optional[int] = None
    max_staff: Optional[int] = None
    active: Optional[bool] = None


class CoverageRequirementResponse(CoverageRequirementBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_modified_by_user_id: Optional[int]

    class Config:
        from_attributes = True