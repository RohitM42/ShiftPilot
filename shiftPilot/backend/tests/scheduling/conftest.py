import pytest
from datetime import date, time


from app.services.scheduling.types import (
    Employee,
    AvailabilityRule,
    AvailabilityType,
    TimeOffRequest,
    Shift,
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