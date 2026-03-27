from pydantic import BaseModel
from typing import List


class EmployeeDepartmentCreate(BaseModel):
    employee_id: int
    department_id: int
    is_primary: bool = False


class EmployeeDepartmentResponse(BaseModel):
    employee_id: int
    department_id: int
    is_primary: bool

    class Config:
        from_attributes = True


class EmployeeDepartmentsListResponse(BaseModel):
    employee_id: int
    departments: List[EmployeeDepartmentResponse]