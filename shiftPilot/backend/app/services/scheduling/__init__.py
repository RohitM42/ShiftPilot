"""
Scheduling service package.

Usage:
    from app.services.scheduling import load_schedule_context, generate_schedule
    context = load_schedule_context(db, store_id=1, week_start=date(2025, 1, 20))
    result = generate_schedule(context)
"""

from .types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    TimeOffRequest,
    CoverageRequirement,
    RoleRequirement,
    Shift,
    TimeSlot,
    ScheduleContext,
    ScheduleResult,
)
from .data_loader import load_schedule_context

__all__ = [
    # Types
    "Employee",
    "AvailabilityRule", 
    "AvailabilityType",
    "TimeOffRequest",
    "CoverageRequirement",
    "RoleRequirement",
    "Shift",
    "TimeSlot",
    "ScheduleContext",
    "ScheduleResult",
    # Functions
    "load_schedule_context",
]