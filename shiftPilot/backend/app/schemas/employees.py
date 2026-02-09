from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
from app.db.models.employees import EmploymentStatus


class EmployeeBase(BaseModel):
    user_id: int
    store_id: int
    is_keyholder: bool = False
    is_manager: bool = False
    employment_status: EmploymentStatus
    contracted_weekly_hours: int
    dob: date


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    store_id: Optional[int] = None
    is_keyholder: Optional[bool] = None
    is_manager: Optional[bool] = None
    employment_status: Optional[EmploymentStatus] = None
    contracted_weekly_hours: Optional[int] = None
    dob: Optional[date] = None


class EmployeeResponse(EmployeeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True