from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional, Literal


class GenerateScheduleRequest(BaseModel):
    store_id: int
    week_start: date
    mode: Literal["add", "replace"] = "add"

    @field_validator("week_start")
    @classmethod
    def must_be_monday(cls, v: date) -> date:
        if v.weekday() != 0:
            raise ValueError(f"week_start must be a Monday, got {v.strftime('%A')}")
        return v


class UnmetCoverageItem(BaseModel):
    department_id: int
    day_of_week: int
    start_time: str  # "HH:MM:SS"
    end_time: str
    min_staff: int  # required staff that couldn't be met

    class Config:
        from_attributes = True


class UnmetRoleItem(BaseModel):
    department_id: Optional[int]  # None = whole store
    day_of_week: Optional[int]
    start_time: str
    end_time: str
    requires_keyholder: bool
    requires_manager: bool
    min_manager_count: int

    class Config:
        from_attributes = True


class GenerateScheduleResponse(BaseModel):
    success: bool
    shifts_created: int
    shift_ids: list[int]
    unmet_coverage: list[UnmetCoverageItem]
    unmet_role_requirements: list[UnmetRoleItem]
    unmet_contracted_hours: dict[str, float]  # str(employee_id) -> hours shortfall
    warnings: list[str]

    class Config:
        from_attributes = True


class PublishBulkRequest(BaseModel):
    shift_ids: list[int]


class PublishBulkResponse(BaseModel):
    published_count: int
