from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional, List

ALL_SHIFT_HOURS = [4, 5, 6, 7, 8, 9, 10, 11, 12]


class StoreBase(BaseModel):
    name: str
    location: str
    timezone: str = "UTC"
    opening_time: time = time(7, 0)
    closing_time: time = time(22, 0)
    allowed_shift_hours: List[int] = ALL_SHIFT_HOURS


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    allowed_shift_hours: Optional[List[int]] = None


class StoreResponse(StoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True