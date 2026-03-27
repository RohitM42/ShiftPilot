from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class LabourBudgetBase(BaseModel):
    store_id: int
    department_id: int
    week_start_date: date
    budget_hours: int


class LabourBudgetCreate(LabourBudgetBase):
    pass


class LabourBudgetUpdate(BaseModel):
    week_start_date: Optional[date] = None
    budget_hours: Optional[int] = None


class LabourBudgetResponse(LabourBudgetBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True