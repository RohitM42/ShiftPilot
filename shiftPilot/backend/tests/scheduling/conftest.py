import pytest
from datetime import date, time

from app.services.scheduling.types import (
    Employee,
    CoverageRequirement,
    RoleRequirement,
)


def get_test_monday() -> date:
    # returns a fixed Monday for deterministic tests
    return date(2025, 1, 20)


@pytest.fixture
def basic_employee() -> Employee:
    # single employee assigned to dept 1 and 2
    return Employee(
        id=1,
        store_id=1,
        is_keyholder=False,
        is_manager=False,
        contracted_weekly_hours=32,
        department_ids=[1, 2],
        primary_department_id=1,
    )


@pytest.fixture
def three_employees() -> list[Employee]:
    # 3 employees: two in dept 1, one in dept 2 only
    return [
        Employee(id=1, store_id=1, is_keyholder=False, is_manager=False,
                 contracted_weekly_hours=32, department_ids=[1], primary_department_id=1),
        Employee(id=2, store_id=1, is_keyholder=False, is_manager=False,
                 contracted_weekly_hours=32, department_ids=[1, 2], primary_department_id=1),
        Employee(id=3, store_id=1, is_keyholder=False, is_manager=False,
                 contracted_weekly_hours=32, department_ids=[2], primary_department_id=2),
    ]


@pytest.fixture
def employees_with_roles() -> list[Employee]:
    return [
        Employee(id=1, store_id=1, is_keyholder=True, is_manager=True,
                 contracted_weekly_hours=40, department_ids=[1], primary_department_id=1),
        Employee(id=2, store_id=1, is_keyholder=True, is_manager=False,
                 contracted_weekly_hours=32, department_ids=[1], primary_department_id=1),
        Employee(id=3, store_id=1, is_keyholder=False, is_manager=False,
                 contracted_weekly_hours=24, department_ids=[1], primary_department_id=1),
    ]


@pytest.fixture
def coverage_req() -> CoverageRequirement:
    return CoverageRequirement(
        id=1, store_id=1, department_id=1, day_of_week=0,
        start_time=time(10, 0), end_time=time(18, 0), min_staff=2, max_staff=4,
    )


@pytest.fixture
def keyholder_req() -> RoleRequirement:
    return RoleRequirement(
        id=1, store_id=1, department_id=None, day_of_week=None,
        start_time=time(6, 0), end_time=time(10, 0),
        requires_keyholder=True, requires_manager=False, min_manager_count=0,
    )


@pytest.fixture
def manager_req() -> RoleRequirement:
    return RoleRequirement(
        id=2, store_id=1, department_id=None, day_of_week=None,
        start_time=time(10, 0), end_time=time(18, 0),
        requires_keyholder=False, requires_manager=True, min_manager_count=1,
    )