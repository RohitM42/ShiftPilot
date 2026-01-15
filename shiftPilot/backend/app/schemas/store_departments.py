from pydantic import BaseModel
from typing import List


class StoreDepartmentCreate(BaseModel):
    store_id: int
    department_id: int


class StoreDepartmentResponse(BaseModel):
    store_id: int
    department_id: int

    class Config:
        from_attributes = True


class StoreDepartmentsListResponse(BaseModel):
    store_id: int
    department_ids: List[int]