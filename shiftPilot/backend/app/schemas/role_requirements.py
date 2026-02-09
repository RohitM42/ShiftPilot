from pydantic import BaseModel
from datetime import time, datetime
from typing import Optional


class RoleRequirementBase(BaseModel):
    store_id: int
    department_id: Optional[int] = None
    day_of_week: Optional[int] = None
    start_time_local: time
    end_time_local: time
    requires_manager: bool = False
    requires_keyholder: bool = False
    min_manager_count: int = 1
    active: bool = True


class RoleRequirementCreate(RoleRequirementBase):
    pass


class RoleRequirementUpdate(BaseModel):
    department_id: Optional[int] = None
    day_of_week: Optional[int] = None
    start_time_local: Optional[time] = None
    end_time_local: Optional[time] = None
    requires_manager: Optional[bool] = None
    requires_keyholder: Optional[bool] = None
    min_manager_count: Optional[int] = None
    active: Optional[bool] = None


class RoleRequirementResponse(RoleRequirementBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_modified_by_user_id: Optional[int]

    class Config:
        from_attributes = True