from pydantic import BaseModel
from typing import Optional


class DepartmentBase(BaseModel):
    name: str
    code: str
    has_manager_role: bool = False


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    has_manager_role: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        from_attributes = True