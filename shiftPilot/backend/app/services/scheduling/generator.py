"""
Schedule generator - main orchestration layer.

This module provides the high-level API for generating schedules,
combining data loading and solving into a single flow.
"""

from datetime import date
from sqlalchemy.orm import Session

from .data_loader import load_schedule_context
from .solver import solve_schedule
from .types import ScheduleContext, ScheduleResult


def generate_schedule(
    db: Session,
    store_id: int,
    week_start: date,
) -> ScheduleResult:
    """
    Generate a schedule for a store for a given week.
    
    main entry point for schedule generation. This function:
    1. Loads all relevant data from the database
    2. Runs the constraint solver
    3. Returns the result with generated shifts
    
    Args:
        db: Database session
        store_id: The store to generate schedule for
        week_start: Monday of the target week
        
    Returns:
        ScheduleResult containing:
        - success: bool indicating if all constraints were met
        - shifts: list of generated Shift objects
        - unmet_coverage: coverage requirements that couldn't be fully satisfied
        - unmet_role_requirements: role requirements that couldn't be met
        - unmet_contracted_hours: dict of employee_id -> hours shortfall
        - warnings: list of warning messages
        
    Raises:
        ValueError: If week_start is not a Monday
        
    Example:
        from datetime import date
        from app.services.scheduling import generate_schedule
        
        result = generate_schedule(db, store_id=1, week_start=date(2025, 1, 20))
        
        if result.success:
            for shift in result.shifts:
                # Save shifts to database
                pass
        else:
            print(f"Warnings: {result.warnings}")
    """
    # Load all data
    context = load_schedule_context(db, store_id, week_start)
    
    # Run solver
    result = solve_schedule(context)
    
    return result


def generate_schedule_from_context(context: ScheduleContext) -> ScheduleResult:
    """
    Generate a schedule from a pre-loaded context.
    
    Useful for testing or when you want to manipulate the context
    before solving.
    
    Args:
        context: Pre-populated ScheduleContext
        
    Returns:
        ScheduleResult with generated shifts
    """
    return solve_schedule(context)