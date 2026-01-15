from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.models.shifts import ShiftStatus, ShiftSource


class ShiftBase(BaseModel):
    store_id: int
    department_id: int
    employee_id: int
    start_datetime_utc: datetime
    end_datetime_utc: datetime
    status: ShiftStatus
    source: ShiftSource


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    department_id: Optional[int] = None
    employee_id: Optional[int] = None
    start_datetime_utc: Optional[datetime] = None
    end_datetime_utc: Optional[datetime] = None
    status: Optional[ShiftStatus] = None


class ShiftResponse(ShiftBase):
    id: int
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True