"""
Seed script for ShiftPilot development database.
Run with: python -m scripts.seed_data_v2
"""

import sys
from datetime import date, time, datetime, timedelta
from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.db.models.users import Users
from app.db.models.stores import Stores
from app.db.models.departments import Departments
from app.db.models.store_departments import StoreDepartment
from app.db.models.user_roles import UserRoles, Role
from app.db.models.employees import Employees, EmploymentStatus
from app.db.models.employee_departments import EmployeeDepartments
from app.db.models.availability_rules import AvailabilityRules, AvailabilityRuleType
from app.db.models.shifts import Shifts, ShiftStatus, ShiftSource
from app.db.models.time_off_requests import TimeOffRequests, TimeOffStatus, TimeOffReason
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.role_requirements import RoleRequirements
from app.db.models.labour_budgets import LabourBudgets


def truncate_tables(db):
    """Truncate all tables except alembic_version in correct order."""
    print("Truncating tables...")
    
    # Disable foreign key checks temporarily and truncate
    tables_to_truncate = [
        "labour_budgets",
        "role_requirements",
        "coverage_requirements",
        "time_off_requests",
        "shifts",
        "availability_rules",
        "employee_departments",
        "employees",
        "user_roles",
        "store_departments",
        "departments",
        "stores",
        "users",
    ]
    
    for table in tables_to_truncate:
        db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
    
    db.commit()
    print("All tables truncated.")


def reset_sequences(db):
    """Reset sequences to start after our seeded IDs."""
    print("Resetting sequences...")
    
    sequences = [
        ("users", "users_id_seq"),
        ("stores", "stores_id_seq"),
        ("departments", "departments_id_seq"),
        ("employees", "employees_id_seq"),
        ("user_roles", "user_roles_id_seq"),
        ("availability_rules", "availability_rules_id_seq"),
        ("shifts", "shifts_id_seq"),
        ("time_off_requests", "time_off_requests_id_seq"),
        ("coverage_requirements", "coverage_requirements_id_seq"),
        ("role_requirements", "role_requirements_id_seq"),
        ("labour_budgets", "labour_budgets_id_seq"),
    ]
    
    for table, seq in sequences:
        db.execute(text(f"SELECT setval('{seq}', (SELECT COALESCE(MAX(id), 1) FROM {table}));"))
    
    db.commit()
    print("Sequences reset.")


def get_current_week_monday():
    """Get the Monday of the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday


def seed_users(db):
    """Seed users: 1 admin, 2 managers, 9 employees."""
    print("Seeding users...")
    
    users = [
        # Admin
        Users(
            id=100001,
            email="admin@shiftpilot.com",
            firstname="Admin",
            surname="User",
            password_hash=get_password_hash("admin123"),
            is_active=True,
        ),
        # Managers
        Users(
            id=100002,
            email="manager1@shiftpilot.com",
            firstname="Manager",
            surname="One",
            password_hash=get_password_hash("manager123"),
            is_active=True,
        ),
        Users(
            id=100003,
            email="manager2@shiftpilot.com",
            firstname="Manager",
            surname="Two",
            password_hash=get_password_hash("manager123"),
            is_active=True,
        ),
        # Employees for Store 1
        Users(
            id=100004,
            email="employee1@shiftpilot.com",
            firstname="Employee",
            surname="One",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100005,
            email="employee2@shiftpilot.com",
            firstname="Employee",
            surname="Two",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100006,
            email="employee3@shiftpilot.com",
            firstname="Employee",
            surname="Three",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100007,
            email="employee4@shiftpilot.com",
            firstname="Employee",
            surname="Four",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employees for Store 2
        Users(
            id=100008,
            email="employee5@shiftpilot.com",
            firstname="Employee",
            surname="Five",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100009,
            email="employee6@shiftpilot.com",
            firstname="Employee",
            surname="Six",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100010,
            email="employee7@shiftpilot.com",
            firstname="Employee",
            surname="Seven",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # New employees for Store 1 coverage
        Users(
            id=100011,
            email="employee8@shiftpilot.com",
            firstname="Employee",
            surname="Eight",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        Users(
            id=100012,
            email="employee9@shiftpilot.com",
            firstname="Employee",
            surname="Nine",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
    ]
    
    for user in users:
        db.add(user)
    db.commit()
    print(f"Seeded {len(users)} users.")


def seed_stores(db):
    """Seed 2 stores."""
    print("Seeding stores...")
    
    stores = [
        Stores(
            id=100001,
            name="Central London",
            location="London",
            timezone="UTC",
        ),
        Stores(
            id=100002,
            name="Central Birmingham",
            location="Birmingham",
            timezone="UTC",
        ),
    ]
    
    for store in stores:
        db.add(store)
    db.commit()
    print(f"Seeded {len(stores)} stores.")


def seed_departments(db):
    """Seed 4 departments."""
    print("Seeding departments...")
    
    departments = [
        Departments(
            id=100001,
            name="Tills",
            code="TILLS",
            has_manager_role=False,
        ),
        Departments(
            id=100002,
            name="Shop Floor",
            code="FLOOR",
            has_manager_role=True,
        ),
        Departments(
            id=100003,
            name="Backstage",
            code="BACK",
            has_manager_role=False,
        ),
        Departments(
            id=100004,
            name="Customer Service",
            code="CS",
            has_manager_role=True,
        ),
    ]
    
    for dept in departments:
        db.add(dept)
    db.commit()
    print(f"Seeded {len(departments)} departments.")


def seed_store_departments(db):
    """Link departments to stores."""
    print("Seeding store-department links...")
    
    links = [
        # Store 1 has all 4 departments
        StoreDepartment(store_id=100001, department_id=100001),  # Tills
        StoreDepartment(store_id=100001, department_id=100002),  # Shop Floor
        StoreDepartment(store_id=100001, department_id=100003),  # Backstage
        StoreDepartment(store_id=100001, department_id=100004),  # Customer Service
        # Store 2 has 3 departments (no Customer Service)
        StoreDepartment(store_id=100002, department_id=100001),  # Tills
        StoreDepartment(store_id=100002, department_id=100002),  # Shop Floor
        StoreDepartment(store_id=100002, department_id=100003),  # Backstage
    ]
    
    for link in links:
        db.add(link)
    db.commit()
    print(f"Seeded {len(links)} store-department links.")


def seed_user_roles(db):
    """Assign roles to users."""
    print("Seeding user roles...")
    
    roles = [
        # Global admin (store_id=None)
        UserRoles(id=100001, user_id=100001, store_id=None, role=Role.ADMIN),
        # Manager 1 -> Store 1
        UserRoles(id=100002, user_id=100002, store_id=100001, role=Role.MANAGER),
        # Manager 2 -> Store 2
        UserRoles(id=100003, user_id=100003, store_id=100002, role=Role.MANAGER),
        # Employees Store 1
        UserRoles(id=100004, user_id=100004, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100005, user_id=100005, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100006, user_id=100006, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100007, user_id=100007, store_id=100001, role=Role.EMPLOYEE),
        # Employees Store 2
        UserRoles(id=100008, user_id=100008, store_id=100002, role=Role.EMPLOYEE),
        UserRoles(id=100009, user_id=100009, store_id=100002, role=Role.EMPLOYEE),
        UserRoles(id=100010, user_id=100010, store_id=100002, role=Role.EMPLOYEE),
        # New employees Store 1
        UserRoles(id=100011, user_id=100011, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100012, user_id=100012, store_id=100001, role=Role.EMPLOYEE),
    ]
    
    for role in roles:
        db.add(role)
    db.commit()
    print(f"Seeded {len(roles)} user roles.")


def seed_employees(db):
    """Create employee records for managers and employees (not admin)."""
    print("Seeding employees...")
    
    # DOBs - varied ages
    employees = [
        # Manager 1 (Store 1)
        Employees(
            id=100001,
            user_id=100002,
            store_id=100001,
            is_keyholder=True,
            is_manager=True,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=40,
            dob=date(1985, 3, 15),
        ),
        # Manager 2 (Store 2)
        Employees(
            id=100002,
            user_id=100003,
            store_id=100002,
            is_keyholder=True,
            is_manager=True,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=40,
            dob=date(1988, 7, 22),
        ),
        # Employee 1 (Store 1)
        Employees(
            id=100003,
            user_id=100004,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1995, 1, 10),
        ),
        # Employee 2 (Store 1)
        Employees(
            id=100004,
            user_id=100005,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(2000, 5, 20),
        ),
        # Employee 3 (Store 1)
        Employees(
            id=100005,
            user_id=100006,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=16,
            dob=date(2002, 11, 8),
        ),
        # Employee 4 (Store 1 - Customer Service)
        Employees(
            id=100006,
            user_id=100007,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(1998, 9, 3),
        ),
        # Employee 5 (Store 2)
        Employees(
            id=100007,
            user_id=100008,
            store_id=100002,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1992, 4, 17),
        ),
        # Employee 6 (Store 2)
        Employees(
            id=100008,
            user_id=100009,
            store_id=100002,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(1999, 12, 25),
        ),
        # Employee 7 (Store 2)
        Employees(
            id=100009,
            user_id=100010,
            store_id=100002,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ON_LEAVE,
            contracted_weekly_hours=20,
            dob=date(2001, 6, 14),
        ),
        # Employee 8 (Store 1) - Keyholder, available weekends, covers Tills
        Employees(
            id=100010,
            user_id=100011,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1997, 2, 28),
        ),
        # Employee 9 (Store 1) - Regular, flexible availability, covers CS + Tills
        Employees(
            id=100011,
            user_id=100012,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(1999, 8, 12),
        ),
    ]
    
    for emp in employees:
        db.add(emp)
    db.commit()
    print(f"Seeded {len(employees)} employees.")


def seed_employee_departments(db):
    """Assign employees to departments."""
    print("Seeding employee-department links...")
    
    links = [
        # Manager 1 - all Store 1 departments
        EmployeeDepartments(employee_id=100001, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100001, department_id=100002, is_primary=False),
        EmployeeDepartments(employee_id=100001, department_id=100003, is_primary=False),
        EmployeeDepartments(employee_id=100001, department_id=100004, is_primary=False),
        # Manager 2 - all Store 2 departments
        EmployeeDepartments(employee_id=100002, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100002, department_id=100002, is_primary=False),
        EmployeeDepartments(employee_id=100002, department_id=100003, is_primary=False),
        # Employee 1 (Store 1) - Tills, Shop Floor
        EmployeeDepartments(employee_id=100003, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100003, department_id=100002, is_primary=False),
        # Employee 2 (Store 1) - Shop Floor, Backstage
        EmployeeDepartments(employee_id=100004, department_id=100002, is_primary=True),
        EmployeeDepartments(employee_id=100004, department_id=100003, is_primary=False),
        # Employee 3 (Store 1) - Backstage only
        EmployeeDepartments(employee_id=100005, department_id=100003, is_primary=True),
        # Employee 4 (Store 1) - Customer Service, Tills
        EmployeeDepartments(employee_id=100006, department_id=100004, is_primary=True),
        EmployeeDepartments(employee_id=100006, department_id=100001, is_primary=False),
        # Employee 5 (Store 2) - Tills, Shop Floor
        EmployeeDepartments(employee_id=100007, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100007, department_id=100002, is_primary=False),
        # Employee 6 (Store 2) - Shop Floor, Backstage
        EmployeeDepartments(employee_id=100008, department_id=100002, is_primary=True),
        EmployeeDepartments(employee_id=100008, department_id=100003, is_primary=False),
        # Employee 7 (Store 2) - Backstage only
        EmployeeDepartments(employee_id=100009, department_id=100003, is_primary=True),
        # Employee 8 (Store 1) - Tills primary, can do Floor
        EmployeeDepartments(employee_id=100010, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100010, department_id=100002, is_primary=False),
        # Employee 9 (Store 1) - CS primary, can do Tills
        EmployeeDepartments(employee_id=100011, department_id=100004, is_primary=True),
        EmployeeDepartments(employee_id=100011, department_id=100001, is_primary=False),
    ]
    
    for link in links:
        db.add(link)
    db.commit()
    print(f"Seeded {len(links)} employee-department links.")


def seed_availability_rules(db):
    """Seed availability rules for employees."""
    print("Seeding availability rules...")
    
    rules = [
        # Employee 1 - Available Mon-Fri 9-18, Unavailable weekends
        AvailabilityRules(id=100001, employee_id=100003, day_of_week=0, start_time_local=time(9, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100002, employee_id=100003, day_of_week=1, start_time_local=time(9, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100003, employee_id=100003, day_of_week=2, start_time_local=time(9, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100004, employee_id=100003, day_of_week=3, start_time_local=time(9, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100005, employee_id=100003, day_of_week=4, start_time_local=time(9, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100006, employee_id=100003, day_of_week=5, start_time_local=None, end_time_local=None, rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100007, employee_id=100003, day_of_week=6, start_time_local=None, end_time_local=None, rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True),
        
        # Employee 2 - Available all week, prefers mornings
        AvailabilityRules(id=100008, employee_id=100004, day_of_week=0, start_time_local=time(6, 0), end_time_local=time(14, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        AvailabilityRules(id=100009, employee_id=100004, day_of_week=1, start_time_local=time(6, 0), end_time_local=time(14, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        AvailabilityRules(id=100010, employee_id=100004, day_of_week=2, start_time_local=time(6, 0), end_time_local=time(14, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        
        # Employee 3 - Part time, only afternoons
        AvailabilityRules(id=100011, employee_id=100005, day_of_week=0, start_time_local=time(14, 0), end_time_local=time(22, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100012, employee_id=100005, day_of_week=2, start_time_local=time(14, 0), end_time_local=time(22, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        AvailabilityRules(id=100013, employee_id=100005, day_of_week=4, start_time_local=time(14, 0), end_time_local=time(22, 0), rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True),
        
        # Employee 5 (Store 2) - Unavailable Wednesdays
        AvailabilityRules(id=100014, employee_id=100007, day_of_week=2, start_time_local=None, end_time_local=None, rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True),
        
        # Employee 6 (Store 2) - Prefers weekends
        AvailabilityRules(id=100015, employee_id=100008, day_of_week=5, start_time_local=time(8, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        AvailabilityRules(id=100016, employee_id=100008, day_of_week=6, start_time_local=time(8, 0), end_time_local=time(18, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        
        # Employee 8 (Store 1) - Available all week including weekends, prefers weekends
        AvailabilityRules(id=100017, employee_id=100010, day_of_week=5, start_time_local=time(6, 0), end_time_local=time(22, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        AvailabilityRules(id=100018, employee_id=100010, day_of_week=6, start_time_local=time(6, 0), end_time_local=time(22, 0), rule_type=AvailabilityRuleType.PREFERRED, priority=2, active=True),
        
        # Employee 9 (Store 1) - Available all week, no specific preferences (fully flexible)
    ]
    
    for rule in rules:
        db.add(rule)
    db.commit()
    print(f"Seeded {len(rules)} availability rules.")


def seed_shifts(db):
    """Seed a week's worth of shifts for current week."""
    print("Seeding shifts...")
    
    monday = get_current_week_monday()
    
    shifts = []
    shift_id = 100001
    
    # Store 1 shifts - each day
    for day_offset in range(7):
        shift_date = monday + timedelta(days=day_offset)
        
        # Morning shift - Employee 1 or 2
        shifts.append(Shifts(
            id=shift_id,
            store_id=100001,
            department_id=100001,  # Tills
            employee_id=100003 if day_offset < 5 else 100004,  # Employee 1 weekdays, Employee 2 weekends
            start_datetime_utc=datetime.combine(shift_date, time(9, 0)),
            end_datetime_utc=datetime.combine(shift_date, time(14, 0)),
            status=ShiftStatus.PUBLISHED,
            source=ShiftSource.MANUAL,
            created_by_user_id=100002,
        ))
        shift_id += 1
        
        # Afternoon shift - Employee 3
        if day_offset in [0, 2, 4]:  # Mon, Wed, Fri
            shifts.append(Shifts(
                id=shift_id,
                store_id=100001,
                department_id=100003,  # Backstage
                employee_id=100005,
                start_datetime_utc=datetime.combine(shift_date, time(14, 0)),
                end_datetime_utc=datetime.combine(shift_date, time(20, 0)),
                status=ShiftStatus.PUBLISHED,
                source=ShiftSource.MANUAL,
                created_by_user_id=100002,
            ))
            shift_id += 1
        
        # Customer Service - Employee 4
        if day_offset < 6:  # Mon-Sat
            shifts.append(Shifts(
                id=shift_id,
                store_id=100001,
                department_id=100004,  # Customer Service
                employee_id=100006,
                start_datetime_utc=datetime.combine(shift_date, time(10, 0)),
                end_datetime_utc=datetime.combine(shift_date, time(16, 0)),
                status=ShiftStatus.PUBLISHED,
                source=ShiftSource.MANUAL,
                created_by_user_id=100002,
            ))
            shift_id += 1
    
    # Store 2 shifts
    for day_offset in range(7):
        shift_date = monday + timedelta(days=day_offset)
        
        # Skip Wednesday for Employee 5 (unavailable)
        if day_offset != 2:
            shifts.append(Shifts(
                id=shift_id,
                store_id=100002,
                department_id=100001,  # Tills
                employee_id=100007,
                start_datetime_utc=datetime.combine(shift_date, time(8, 0)),
                end_datetime_utc=datetime.combine(shift_date, time(16, 0)),
                status=ShiftStatus.PUBLISHED,
                source=ShiftSource.MANUAL,
                created_by_user_id=100003,
            ))
            shift_id += 1
        
        # Employee 6 - prefers weekends but works some weekdays
        if day_offset in [1, 3, 5, 6]:  # Tue, Thu, Sat, Sun
            shifts.append(Shifts(
                id=shift_id,
                store_id=100002,
                department_id=100002,  # Shop Floor
                employee_id=100008,
                start_datetime_utc=datetime.combine(shift_date, time(10, 0)),
                end_datetime_utc=datetime.combine(shift_date, time(18, 0)),
                status=ShiftStatus.PUBLISHED,
                source=ShiftSource.MANUAL,
                created_by_user_id=100003,
            ))
            shift_id += 1
    
    # Add a couple of draft shifts
    shifts.append(Shifts(
        id=shift_id,
        store_id=100001,
        department_id=100002,
        employee_id=100004,
        start_datetime_utc=datetime.combine(monday + timedelta(days=7), time(9, 0)),
        end_datetime_utc=datetime.combine(monday + timedelta(days=7), time(17, 0)),
        status=ShiftStatus.DRAFT,
        source=ShiftSource.AI,
        created_by_user_id=100002,
    ))
    shift_id += 1
    
    shifts.append(Shifts(
        id=shift_id,
        store_id=100002,
        department_id=100003,
        employee_id=100009,  # Employee 7 (on leave)
        start_datetime_utc=datetime.combine(monday + timedelta(days=8), time(12, 0)),
        end_datetime_utc=datetime.combine(monday + timedelta(days=8), time(20, 0)),
        status=ShiftStatus.CANCELLED,
        source=ShiftSource.MANUAL,
        created_by_user_id=100003,
    ))
    
    for shift in shifts:
        db.add(shift)
    db.commit()
    print(f"Seeded {len(shifts)} shifts.")


def seed_time_off_requests(db):
    """Seed time off requests in various statuses."""
    print("Seeding time off requests...")
    
    monday = get_current_week_monday()
    
    requests = [
        # Approved holiday - Employee 7 (explains ON_LEAVE status)
        TimeOffRequests(
            id=100001,
            employee_id=100009,
            start_date=datetime.combine(monday - timedelta(days=3), time(0, 0)),
            end_date=datetime.combine(monday + timedelta(days=10), time(23, 59)),
            status=TimeOffStatus.APPROVED,
            reason_type=TimeOffReason.HOLIDAY,
            comments="Annual leave - family holiday",
            last_modified_by_user_id=100003,
        ),
        # Pending request - Employee 2
        TimeOffRequests(
            id=100002,
            employee_id=100004,
            start_date=datetime.combine(monday + timedelta(days=14), time(0, 0)),
            end_date=datetime.combine(monday + timedelta(days=16), time(23, 59)),
            status=TimeOffStatus.PENDING,
            reason_type=TimeOffReason.HOLIDAY,
            comments="Long weekend trip",
            last_modified_by_user_id=None,
        ),
        # Rejected request - Employee 5
        TimeOffRequests(
            id=100003,
            employee_id=100007,
            start_date=datetime.combine(monday + timedelta(days=2), time(0, 0)),
            end_date=datetime.combine(monday + timedelta(days=2), time(23, 59)),
            status=TimeOffStatus.REJECTED,
            reason_type=TimeOffReason.OTHER,
            comments="Personal appointment",
            last_modified_by_user_id=100003,
        ),
        # Sick leave - Employee 6
        TimeOffRequests(
            id=100004,
            employee_id=100008,
            start_date=datetime.combine(monday - timedelta(days=7), time(0, 0)),
            end_date=datetime.combine(monday - timedelta(days=5), time(23, 59)),
            status=TimeOffStatus.APPROVED,
            reason_type=TimeOffReason.SICK_LEAVE,
            comments="Flu",
            last_modified_by_user_id=100003,
        ),
    ]
    
    for req in requests:
        db.add(req)
    db.commit()
    print(f"Seeded {len(requests)} time off requests.")


def seed_coverage_requirements(db):
    """Seed coverage requirements for stores."""
    print("Seeding coverage requirements...")
    
    requirements = []
    req_id = 100001
    
    # Store 1 - Tills needs 2 people during peak hours
    for day in range(7):
        requirements.append(CoverageRequirements(
            id=req_id,
            store_id=100001,
            department_id=100001,
            day_of_week=day,
            start_time_local=time(10, 0),
            end_time_local=time(16, 0),
            min_staff=2,
            max_staff=3,
            active=True,
            last_modified_by_user_id=100001,
        ))
        req_id += 1
    
    # Store 1 - Customer Service needs 1 person
    for day in range(6):  # Mon-Sat
        requirements.append(CoverageRequirements(
            id=req_id,
            store_id=100001,
            department_id=100004,
            day_of_week=day,
            start_time_local=time(9, 0),
            end_time_local=time(18, 0),
            min_staff=1,
            max_staff=2,
            active=True,
            last_modified_by_user_id=100001,
        ))
        req_id += 1
    
    # Store 2 - Tills needs 1-2 people
    for day in range(7):
        requirements.append(CoverageRequirements(
            id=req_id,
            store_id=100002,
            department_id=100001,
            day_of_week=day,
            start_time_local=time(8, 0),
            end_time_local=time(20, 0),
            min_staff=1,
            max_staff=2,
            active=True,
            last_modified_by_user_id=100001,
        ))
        req_id += 1
    
    for req in requirements:
        db.add(req)
    db.commit()
    print(f"Seeded {len(requirements)} coverage requirements.")


def seed_role_requirements(db):
    """Seed role requirements (keyholder/manager needed)."""
    print("Seeding role requirements...")
    
    requirements = [
        # Store 1 - needs keyholder for opening (6-10am)
        RoleRequirements(
            id=100001,
            store_id=100001,
            department_id=None,  # Whole store
            day_of_week=None,  # Every day
            start_time_local=time(6, 0),
            end_time_local=time(10, 0),
            requires_manager=False,
            requires_keyholder=True,
            min_manager_count=0,
            active=True,
            last_modified_by_user_id=100001,
        ),
        # Store 1 - needs keyholder for closing (18-22pm)
        RoleRequirements(
            id=100002,
            store_id=100001,
            department_id=None,
            day_of_week=None,
            start_time_local=time(18, 0),
            end_time_local=time(22, 0),
            requires_manager=False,
            requires_keyholder=True,
            min_manager_count=0,
            active=True,
            last_modified_by_user_id=100001,
        ),
        # Store 2 - needs keyholder all day on weekends
        RoleRequirements(
            id=100003,
            store_id=100002,
            department_id=None,
            day_of_week=5,  # Saturday
            start_time_local=time(8, 0),
            end_time_local=time(20, 0),
            requires_manager=False,
            requires_keyholder=True,
            min_manager_count=0,
            active=True,
            last_modified_by_user_id=100001,
        ),
        RoleRequirements(
            id=100004,
            store_id=100002,
            department_id=None,
            day_of_week=6,  # Sunday
            start_time_local=time(10, 0),
            end_time_local=time(18, 0),
            requires_manager=False,
            requires_keyholder=True,
            min_manager_count=0,
            active=True,
            last_modified_by_user_id=100001,
        ),
    ]
    
    for req in requirements:
        db.add(req)
    db.commit()
    print(f"Seeded {len(requirements)} role requirements.")


def seed_labour_budgets(db):
    """Seed labour budgets for current and next week."""
    print("Seeding labour budgets...")
    
    monday = get_current_week_monday()
    next_monday = monday + timedelta(days=7)
    
    budgets = [
        # Store 1 - Current week
        LabourBudgets(id=100001, store_id=100001, department_id=100001, week_start_date=monday, budget_hours=80),
        LabourBudgets(id=100002, store_id=100001, department_id=100002, week_start_date=monday, budget_hours=60),
        LabourBudgets(id=100003, store_id=100001, department_id=100003, week_start_date=monday, budget_hours=40),
        LabourBudgets(id=100004, store_id=100001, department_id=100004, week_start_date=monday, budget_hours=36),
        # Store 1 - Next week
        LabourBudgets(id=100005, store_id=100001, department_id=100001, week_start_date=next_monday, budget_hours=85),
        LabourBudgets(id=100006, store_id=100001, department_id=100002, week_start_date=next_monday, budget_hours=65),
        LabourBudgets(id=100007, store_id=100001, department_id=100003, week_start_date=next_monday, budget_hours=45),
        LabourBudgets(id=100008, store_id=100001, department_id=100004, week_start_date=next_monday, budget_hours=36),
        # Store 2 - Current week
        LabourBudgets(id=100009, store_id=100002, department_id=100001, week_start_date=monday, budget_hours=70),
        LabourBudgets(id=100010, store_id=100002, department_id=100002, week_start_date=monday, budget_hours=50),
        LabourBudgets(id=100011, store_id=100002, department_id=100003, week_start_date=monday, budget_hours=30),
        # Store 2 - Next week
        LabourBudgets(id=100012, store_id=100002, department_id=100001, week_start_date=next_monday, budget_hours=75),
        LabourBudgets(id=100013, store_id=100002, department_id=100002, week_start_date=next_monday, budget_hours=55),
        LabourBudgets(id=100014, store_id=100002, department_id=100003, week_start_date=next_monday, budget_hours=35),
    ]
    
    for budget in budgets:
        db.add(budget)
    db.commit()
    print(f"Seeded {len(budgets)} labour budgets.")


def main():
    """Main seed function."""
    print("\n" + "="*50)
    print("ShiftPilot Database Seeder")
    print("="*50 + "\n")
    
    # Confirmation prompt
    response = input("This will DELETE ALL EXISTING DATA (except alembic versions). Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    
    db = SessionLocal()
    
    try:
        # Truncate all tables
        truncate_tables(db)
        
        # Seed in dependency order
        seed_users(db)
        seed_stores(db)
        seed_departments(db)
        seed_store_departments(db)
        seed_user_roles(db)
        seed_employees(db)
        seed_employee_departments(db)
        seed_availability_rules(db)
        seed_shifts(db)
        seed_time_off_requests(db)
        seed_coverage_requirements(db)
        seed_role_requirements(db)
        seed_labour_budgets(db)
        
        # Reset sequences
        reset_sequences(db)
        
        print("\n" + "="*50)
        print("Seeding complete!")
        print("="*50)
        print("\nTest accounts:")
        print("  Admin:    admin@shiftpilot.com / admin123")
        print("  Manager1: manager1@shiftpilot.com / manager123")
        print("  Manager2: manager2@shiftpilot.com / manager123")
        print("  Employee: employee1@shiftpilot.com / employee123")
        print("            (employee 2-9 follow same pattern)")
        print("="*50 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()