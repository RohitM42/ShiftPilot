from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional


class StoreBase(BaseModel):
    name: str
    location: str
    timezone: str = "UTC"
    opening_time: time = time(7, 0)
    closing_time: time = time(22, 0)


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None


class StoreResponse(StoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True