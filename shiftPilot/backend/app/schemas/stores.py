from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StoreBase(BaseModel):
    name: str
    location: str
    timezone: str = "UTC"


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None


class StoreResponse(StoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True