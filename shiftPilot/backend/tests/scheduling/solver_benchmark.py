"""
Solver benchmark: OR-Tools CP-SAT vs greedy solver, and OR-Tools granularity comparison.

Usage (from backend/ with venv active):
    python tests/scheduling/solver_benchmark.py

Outputs a summary table to stdout comparing:
  - Solve time (wall-clock seconds)
  - Shifts generated
  - Unmet coverage requirements
  - Unmet role requirements

Scenarios tested at three complexity levels:
  SMALL  — 3 employees, 1 department, simple weekday coverage
  MEDIUM — 8 employees, 2 departments, mixed weekday/weekend coverage + role reqs
  LARGE  — 15 employees, 4 departments, full-week coverage + role reqs + availability constraints

Granularity comparison (OR solver only):
  60-min slots (default) vs 30-min slots on the MEDIUM scenario.
  The 30-min comparison patches SLOT_DURATION_MINUTES at import level using importlib.
"""

import time
import sys
import os
from datetime import date, time as dtime, datetime, timedelta
from typing import Optional
import importlib
import unittest.mock

# Make sure app package is importable when run from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.scheduling.types import (
    Employee, AvailabilityRule, CoverageRequirement, RoleRequirement,
    ScheduleContext, ScheduleResult, AvailabilityType, Shift, TimeOffRequest,
)
from app.services.scheduling import or_solver as _or_solver_module
from app.services.scheduling.or_solver import solve_schedule as or_solve
from app.services.scheduling.solver import ScheduleSolver


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

WEEK_START = date(2026, 4, 6)  # Monday

def _emp(id: int, contracted: int, dept_ids: list[int], primary: int,
         keyholder: bool = False, manager: bool = False) -> Employee:
    return Employee(
        id=id, store_id=1,
        is_keyholder=keyholder, is_manager=manager,
        contracted_weekly_hours=contracted,
        department_ids=dept_ids,
        primary_department_id=primary,
    )


def _cov(id: int, dept: int, dow: int, start: dtime, end: dtime, min_staff: int) -> CoverageRequirement:
    return CoverageRequirement(
        id=id, store_id=1, department_id=dept,
        day_of_week=dow, start_time=start, end_time=end,
        min_staff=min_staff,
    )


def _role(id: int, dow: Optional[int], start: dtime, end: dtime,
          keyholder: bool = False, manager: bool = False) -> RoleRequirement:
    return RoleRequirement(
        id=id, store_id=1, department_id=None,
        day_of_week=dow, start_time=start, end_time=end,
        requires_keyholder=keyholder, requires_manager=manager,
        min_manager_count=1 if manager else 0,
    )


def _avail(emp_id: int, dow: int, rule_type: AvailabilityType,
           start: Optional[dtime] = None, end: Optional[dtime] = None) -> AvailabilityRule:
    return AvailabilityRule(
        employee_id=emp_id, day_of_week=dow,
        rule_type=rule_type, start_time=start, end_time=end,
    )


# --- SMALL scenario: 3 employees, 1 department, simple weekday coverage ---
def build_small() -> ScheduleContext:
    employees = [
        _emp(1, 37, [1], 1, keyholder=True, manager=True),
        _emp(2, 37, [1], 1),
        _emp(3, 20, [1], 1),
    ]
    # Mon-Fri, 09:00–17:00, min 1 staff
    coverage = [
        _cov(i + 1, 1, dow, dtime(9, 0), dtime(17, 0), 1)
        for i, dow in enumerate(range(5))
    ]
    return ScheduleContext(
        store_id=1, week_start=WEEK_START,
        employees=employees,
        availability_rules=[],
        time_off_requests=[],
        coverage_requirements=coverage,
        role_requirements=[],
    )


# --- MEDIUM scenario: 8 employees, 2 departments, mixed coverage + role reqs ---
def build_medium() -> ScheduleContext:
    employees = [
        _emp(1, 40, [1, 2], 1, keyholder=True, manager=True),
        _emp(2, 37, [1, 2], 1, keyholder=True),
        _emp(3, 37, [1], 1, keyholder=True),
        _emp(4, 30, [1], 1),
        _emp(5, 24, [2], 2),
        _emp(6, 20, [2], 2),
        _emp(7, 16, [1, 2], 1),
        _emp(8, 16, [2], 2),
    ]
    coverage = []
    cid = 1
    for dow in range(5):  # Mon-Fri
        coverage.append(_cov(cid, 1, dow, dtime(8, 0), dtime(14, 0), 2)); cid += 1
        coverage.append(_cov(cid, 1, dow, dtime(14, 0), dtime(22, 0), 1)); cid += 1
        coverage.append(_cov(cid, 2, dow, dtime(9, 0), dtime(17, 0), 1)); cid += 1
    for dow in range(5, 7):  # Sat-Sun
        coverage.append(_cov(cid, 1, dow, dtime(9, 0), dtime(18, 0), 2)); cid += 1
        coverage.append(_cov(cid, 2, dow, dtime(10, 0), dtime(16, 0), 1)); cid += 1

    role_reqs = [
        _role(1, None, dtime(8, 0), dtime(10, 0), keyholder=True),   # every day: opening keyholder
        _role(2, None, dtime(20, 0), dtime(22, 0), keyholder=True),  # every day: closing keyholder
        _role(3, None, dtime(9, 0), dtime(17, 0), manager=True),     # every day: manager present
    ]

    avail = [
        _avail(7, 0, AvailabilityType.UNAVAILABLE),  # emp 7 unavailable Mon
        _avail(7, 6, AvailabilityType.UNAVAILABLE),  # emp 7 unavailable Sun
        _avail(8, 5, AvailabilityType.UNAVAILABLE),  # emp 8 unavailable Sat
        _avail(8, 6, AvailabilityType.UNAVAILABLE),  # emp 8 unavailable Sun
    ]

    return ScheduleContext(
        store_id=1, week_start=WEEK_START,
        employees=employees,
        availability_rules=avail,
        time_off_requests=[],
        coverage_requirements=coverage,
        role_requirements=role_reqs,
    )


# --- LARGE scenario: 15 employees, 4 departments, full week + availability constraints ---
def build_large() -> ScheduleContext:
    employees = [
        _emp(1,  40, [1, 2, 3, 4], 1, keyholder=True, manager=True),
        _emp(2,  37, [1, 2],       1, keyholder=True),
        _emp(3,  37, [1, 3],       1, keyholder=True),
        _emp(4,  37, [2, 4],       2, keyholder=True),
        _emp(5,  30, [1],          1),
        _emp(6,  30, [2],          2),
        _emp(7,  24, [3],          3),
        _emp(8,  24, [4],          4),
        _emp(9,  24, [1, 2],       1),
        _emp(10, 20, [2, 3],       2),
        _emp(11, 20, [3, 4],       3),
        _emp(12, 16, [1],          1),
        _emp(13, 16, [2],          2),
        _emp(14, 16, [4],          4),
        _emp(15, 16, [1, 3],       1),
    ]

    coverage = []
    cid = 1
    for dept in [1, 2, 3, 4]:
        for dow in range(7):
            is_weekend = dow >= 5
            min_s = 3 if is_weekend else 2
            coverage.append(_cov(cid, dept, dow, dtime(8, 0), dtime(14, 0), min_s)); cid += 1
            coverage.append(_cov(cid, dept, dow, dtime(14, 0), dtime(20, 0), min_s - 1 if min_s > 1 else 1)); cid += 1

    role_reqs = [
        _role(1, None, dtime(7, 0), dtime(9, 0), keyholder=True),
        _role(2, None, dtime(19, 0), dtime(22, 0), keyholder=True),
        _role(3, None, dtime(9, 0), dtime(17, 0), manager=True),
    ]

    avail = []
    # Various day-off constraints
    for dow in [5, 6]:
        avail.append(_avail(5, dow, AvailabilityType.UNAVAILABLE))
        avail.append(_avail(8, dow, AvailabilityType.UNAVAILABLE))
    avail.append(_avail(12, 0, AvailabilityType.UNAVAILABLE))
    avail.append(_avail(12, 1, AvailabilityType.UNAVAILABLE))
    avail.append(_avail(13, 6, AvailabilityType.UNAVAILABLE))
    avail.append(_avail(14, 5, AvailabilityType.UNAVAILABLE))
    avail.append(_avail(14, 6, AvailabilityType.UNAVAILABLE))

    return ScheduleContext(
        store_id=1, week_start=WEEK_START,
        employees=employees,
        availability_rules=avail,
        time_off_requests=[],
        coverage_requirements=coverage,
        role_requirements=role_reqs,
    )


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------

def run_or(context: ScheduleContext) -> tuple[ScheduleResult, float]:
    t0 = time.perf_counter()
    result = or_solve(context)
    return result, time.perf_counter() - t0


def run_greedy(context: ScheduleContext) -> tuple[ScheduleResult, float]:
    t0 = time.perf_counter()
    result = ScheduleSolver(context).solve()
    return result, time.perf_counter() - t0


def run_or_30min(context: ScheduleContext) -> tuple[ScheduleResult, float]:
    """Run OR solver with SLOT_DURATION_MINUTES patched to 30."""
    with unittest.mock.patch.object(_or_solver_module, 'SLOT_DURATION_MINUTES', 30):
        with unittest.mock.patch.object(_or_solver_module, 'SLOTS_PER_HOUR', 2):
            with unittest.mock.patch.object(_or_solver_module, 'SLOTS_PER_DAY',
                                            (_or_solver_module.DAY_END_HOUR - _or_solver_module.DAY_START_HOUR) * 2):
                t0 = time.perf_counter()
                result = or_solve(context)
                elapsed = time.perf_counter() - t0
    return result, elapsed


def summarise(result: ScheduleResult, is_or: bool = False) -> dict:
    if is_or:
        # OR solver: warnings list is empty when CP-SAT proved optimality, has one entry if time limit hit.
        # Note: OPTIMAL here means best achievable objective — all constraints are soft-weighted, so
        # unmet requirements can still appear even on an OPTIMAL result if staffing makes them infeasible.
        status = "FEASIBLE*" if result.warnings else "OPTIMAL†"
    else:
        status = "—"
    return {
        "shifts": len(result.shifts),
        "unmet_cov": len(result.unmet_coverage),
        "unmet_role": len(result.unmet_role_requirements),
        "status": status,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

N_PASSES = 10  # number of passes to average timing over


def bench(run_fn, context, is_or: bool) -> tuple[dict, float, float]:
    """Run run_fn N_PASSES times; return (summarised result, mean time, std time).
    Constraint counts are taken from the first pass — they are deterministic."""
    times = []
    first_result = None
    for i in range(N_PASSES):
        result, elapsed = run_fn(context)
        times.append(elapsed)
        if first_result is None:
            first_result = result
    mean_t = sum(times) / N_PASSES
    variance = sum((t - mean_t) ** 2 for t in times) / N_PASSES
    std_t = variance ** 0.5
    return summarise(first_result, is_or=is_or), mean_t, std_t


def main():
    scenarios = [
        ("SMALL",  build_small()),
        ("MEDIUM", build_medium()),
        ("LARGE",  build_large()),
    ]

    rows = []
    medium_context = None

    print(f"\nRunning solver benchmarks ({N_PASSES} passes each)...\n")

    for name, ctx in scenarios:
        if name == "MEDIUM":
            medium_context = ctx

        print(f"  {name}...")
        or_s,  or_mean,  or_std  = bench(run_or,     ctx, is_or=True)
        gr_s,  gr_mean,  gr_std  = bench(run_greedy,  ctx, is_or=False)

        rows.append((name, "OR-Tools (60 min)", or_mean, or_std, or_s))
        rows.append((name, "Greedy",            gr_mean, gr_std, gr_s))

    # Granularity comparison on MEDIUM only
    print("  MEDIUM (granularity)...")
    or60_s, or60_mean, or60_std = bench(run_or,       medium_context, is_or=True)
    or30_s, or30_mean, or30_std = bench(run_or_30min, medium_context, is_or=True)
    rows.append(("MEDIUM (granularity)", "OR-Tools (60 min)", or60_mean, or60_std, or60_s))
    rows.append(("MEDIUM (granularity)", "OR-Tools (30 min)", or30_mean, or30_std, or30_s))

    # Print table
    header = f"{'Scenario':<26} {'Solver':<22} {'Avg (s)':>9} {'±Std':>6} {'Shifts':>7} {'Unmet Cov':>10} {'Unmet Role':>11} {'Status':>9}"
    divider = "-" * len(header)
    print()
    print(header)
    print(divider)
    for (scenario, solver, mean_t, std_t, s) in rows:
        print(
            f"{scenario:<26} {solver:<22} {mean_t:>9.3f} {std_t:>6.3f} "
            f"{s['shifts']:>7} {s['unmet_cov']:>10} {s['unmet_role']:>11} {s['status']:>9}"
        )
    print(divider)
    print()
    print("Notes:")
    print(f"  Timing is the mean over {N_PASSES} passes; ±Std is the population standard deviation.")
    print("  Constraint counts are deterministic (same input = same result) and taken from the first pass.")
    print("  † OPTIMAL: CP-SAT proved no better objective value exists. All constraints are soft-weighted")
    print("    penalties, so unmet requirements on an OPTIMAL result are infeasible given the staffing,")
    print("    not a solver error.")
    print("  * FEASIBLE: time limit (120 s) hit; solution returned but optimality not proven.")
    print("  - Greedy solver is a heuristic: no optimality guarantee, faster but more unmet constraints.")
    print()


if __name__ == "__main__":
    main()
