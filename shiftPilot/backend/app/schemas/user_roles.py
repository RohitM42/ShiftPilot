from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.models.user_roles import Role


class UserRoleCreate(BaseModel):
    user_id: int
    store_id: Optional[int] = None
    role: Role


class UserRoleUpdate(BaseModel):
    role: Optional[Role] = None


class UserRoleResponse(BaseModel):
    id: int
    user_id: int
    store_id: Optional[int]
    role: Role
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True