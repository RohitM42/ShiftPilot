"""
Internal data types for scheduling logic.
decoupled from SQLAlchemy models for cleaner logic.
"""

from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from enum import Enum
from typing import Optional


class AvailabilityType(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PREFERRED = "PREFERRED"


@dataclass
class Employee:
    id: int
    store_id: int
    is_keyholder: bool
    is_manager: bool
    contracted_weekly_hours: int
    department_ids: list[int] = field(default_factory=list)
    primary_department_id: Optional[int] = None


@dataclass
class AvailabilityRule:
    employee_id: int
    day_of_week: int  # 0-6
    rule_type: AvailabilityType
    start_time: Optional[time] = None  # None means all day
    end_time: Optional[time] = None


@dataclass
class TimeOffRequest:
    employee_id: int
    start_datetime: datetime
    end_datetime: datetime


@dataclass
class CoverageRequirement:
    id: int
    store_id: int
    department_id: int
    day_of_week: int
    start_time: time
    end_time: time
    min_staff: int
    max_staff: Optional[int] = None


@dataclass
class RoleRequirement:
    id: int
    store_id: int
    department_id: Optional[int]  # None = whole store
    day_of_week: Optional[int]  # None = every day
    start_time: time
    end_time: time
    requires_keyholder: bool
    requires_manager: bool
    min_manager_count: int


@dataclass
class Shift:
    """A shift assignment (proposed or final)."""
    employee_id: int
    store_id: int
    department_id: int
    start_datetime: datetime
    end_datetime: datetime
    
    @property
    def duration_hours(self) -> float:
        delta = self.end_datetime - self.start_datetime
        return delta.total_seconds() / 3600
    
    @property
    def day_of_week(self) -> int:
        return self.start_datetime.weekday()


@dataclass
class TimeSlot:
    """Represents a coverage window that needs staffing."""
    day_of_week: int
    start_time: time
    end_time: time
    department_id: int
    min_staff: int
    max_staff: Optional[int] = None
    
    def to_datetime_range(self, week_start: date) -> tuple[datetime, datetime]:
        """Convert to absolute datetime range given a week start (Monday)."""
        slot_date = week_start + timedelta(days=self.day_of_week)
        start_dt = datetime.combine(slot_date, self.start_time)
        end_dt = datetime.combine(slot_date, self.end_time)
        return start_dt, end_dt


@dataclass
class ScheduleContext:
    """All data needed to generate a schedule for one store/week."""
    store_id: int
    week_start: date  # Monday
    employees: list[Employee]
    availability_rules: list[AvailabilityRule]
    time_off_requests: list[TimeOffRequest]
    coverage_requirements: list[CoverageRequirement]
    role_requirements: list[RoleRequirement]
    existing_shifts: list[Shift] = field(default_factory=list)
    
    @property
    def week_end(self) -> date:
        """Sunday of the schedule week."""
        return self.week_start + timedelta(days=6)


@dataclass
class ScheduleResult:
    """Output of the scheduling algorithm."""
    success: bool
    shifts: list[Shift]
    unmet_coverage: list[CoverageRequirement] = field(default_factory=list)
    unmet_role_requirements: list[RoleRequirement] = field(default_factory=list)
    unmet_contracted_hours: dict[int, float] = field(default_factory=dict)  # employee_id -> shortfall
    warnings: list[str] = field(default_factory=list)