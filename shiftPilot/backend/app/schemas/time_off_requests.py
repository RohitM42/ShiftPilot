from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.models.time_off_requests import TimeOffStatus, TimeOffReason


class TimeOffRequestBase(BaseModel):
    employee_id: int
    start_date: datetime
    end_date: datetime
    reason_type: TimeOffReason
    comments: Optional[str] = None


class TimeOffRequestCreate(TimeOffRequestBase):
    pass


class TimeOffRequestUpdate(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[TimeOffStatus] = None
    reason_type: Optional[TimeOffReason] = None
    comments: Optional[str] = None


class TimeOffRequestResponse(TimeOffRequestBase):
    id: int
    status: TimeOffStatus
    created_at: datetime
    updated_at: datetime
    last_modified_by_user_id: Optional[int]

    class Config:
        from_attributes = True