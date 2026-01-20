"""
Scheduling service package.

Usage:
    from datetime import date
    from app.services.scheduling import generate_schedule
    
    # Simple usage - load data and solve in one call
    result = generate_schedule(db, store_id=1, week_start=date(2025, 1, 20))
    
    # Or load context separately for inspection/testing
    from app.services.scheduling import load_schedule_context, generate_schedule_from_context
    
    context = load_schedule_context(db, store_id=1, week_start=date(2025, 1, 20))
    result = generate_schedule_from_context(context)
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
from .generator import generate_schedule, generate_schedule_from_context
from .solver import solve_schedule

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
    # Main entry points
    "generate_schedule",
    "generate_schedule_from_context",
    # Lower-level functions
    "load_schedule_context",
    "solve_schedule",
]