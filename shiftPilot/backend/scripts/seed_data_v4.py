"""
Seed script for ShiftPilot development database - SIMPLIFIED VERSION (v4)

Simplifications from v3:
- Single store only (Store 1)
- 7 employees instead of 9 (removed 100011, 100012)
- Keyholder requirements: 7-10am and 17-21pm (narrower windows)
- CS coverage: Mon-Fri only (no Sat)
- All keyholders available 6am-22pm for flexibility
- No existing shifts (clean slate for solver)
- No time off requests

Run with: python -m scripts.seed_data_v4
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
    """Seed users: 1 admin, 1 manager, 6 employees."""
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
        # Manager (Store 1)
        Users(
            id=100002,
            email="manager1@shiftpilot.com",
            firstname="Manager",
            surname="One",
            password_hash=get_password_hash("manager123"),
            is_active=True,
        ),
        # Employee 1 - Keyholder, Tills primary
        Users(
            id=100003,
            email="employee1@shiftpilot.com",
            firstname="Alice",
            surname="Smith",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employee 2 - Regular, Shop Floor primary
        Users(
            id=100004,
            email="employee2@shiftpilot.com",
            firstname="Bob",
            surname="Jones",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employee 3 - Keyholder, CS primary (evening specialist)
        Users(
            id=100005,
            email="employee3@shiftpilot.com",
            firstname="Carol",
            surname="Williams",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employee 4 - Regular, CS primary
        Users(
            id=100006,
            email="employee4@shiftpilot.com",
            firstname="David",
            surname="Brown",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employee 5 - Keyholder, Tills primary (morning specialist)
        Users(
            id=100007,
            email="employee5@shiftpilot.com",
            firstname="Emma",
            surname="Davis",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
        # Employee 6 - Keyholder, flexible all departments
        Users(
            id=100008,
            email="employee6@shiftpilot.com",
            firstname="Frank",
            surname="Miller",
            password_hash=get_password_hash("employee123"),
            is_active=True,
        ),
    ]
    
    for user in users:
        db.add(user)
    db.commit()
    print(f"Seeded {len(users)} users.")


def seed_stores(db):
    """Seed 1 store."""
    print("Seeding stores...")
    
    stores = [
        Stores(
            id=100001,
            name="Central London",
            location="London",
            timezone="UTC",
        ),
    ]
    
    for store in stores:
        db.add(store)
    db.commit()
    print(f"Seeded {len(stores)} stores.")


def seed_departments(db):
    """Seed 3 departments (simplified from 4)."""
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
    """Link departments to store."""
    print("Seeding store-department links...")
    
    links = [
        StoreDepartment(store_id=100001, department_id=100001),  # Tills
        StoreDepartment(store_id=100001, department_id=100002),  # Shop Floor
        StoreDepartment(store_id=100001, department_id=100003),  # Customer Service
    ]
    
    for link in links:
        db.add(link)
    db.commit()
    print(f"Seeded {len(links)} store-department links.")


def seed_user_roles(db):
    """Assign roles to users."""
    print("Seeding user roles...")
    
    roles = [
        UserRoles(id=100001, user_id=100001, store_id=None, role=Role.ADMIN),
        UserRoles(id=100002, user_id=100002, store_id=100001, role=Role.MANAGER),
        UserRoles(id=100003, user_id=100003, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100004, user_id=100004, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100005, user_id=100005, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100006, user_id=100006, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100007, user_id=100007, store_id=100001, role=Role.EMPLOYEE),
        UserRoles(id=100008, user_id=100008, store_id=100001, role=Role.EMPLOYEE),
    ]
    
    for role in roles:
        db.add(role)
    db.commit()
    print(f"Seeded {len(roles)} user roles.")


def seed_employees(db):
    """Create employee records."""
    print("Seeding employees...")
    
    employees = [
        # Manager (40h, all depts, keyholder)
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
        # Employee 1 - Alice (32h, Keyholder, Tills primary)
        Employees(
            id=100002,
            user_id=100003,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1995, 1, 10),
        ),
        # Employee 2 - Bob (24h, Regular, Shop Floor)
        Employees(
            id=100003,
            user_id=100004,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(2000, 5, 20),
        ),
        # Employee 3 - Carol (24h, Keyholder, CS - evening specialist)
        Employees(
            id=100004,
            user_id=100005,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(2002, 11, 8),
        ),
        # Employee 4 - David (24h, Regular, CS)
        Employees(
            id=100005,
            user_id=100006,
            store_id=100001,
            is_keyholder=False,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=24,
            dob=date(1998, 9, 3),
        ),
        # Employee 5 - Emma (32h, Keyholder, Tills - morning specialist)
        Employees(
            id=100006,
            user_id=100007,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1997, 2, 28),
        ),
        # Employee 6 - Frank (32h, Keyholder, flexible)
        Employees(
            id=100007,
            user_id=100008,
            store_id=100001,
            is_keyholder=True,
            is_manager=False,
            employment_status=EmploymentStatus.ACTIVE,
            contracted_weekly_hours=32,
            dob=date(1994, 7, 10),
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
        # Manager - all departments
        EmployeeDepartments(employee_id=100001, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100001, department_id=100002, is_primary=False),
        EmployeeDepartments(employee_id=100001, department_id=100003, is_primary=False),
        
        # Alice - Tills primary, can do CS
        EmployeeDepartments(employee_id=100002, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100002, department_id=100003, is_primary=False),
        
        # Bob - Shop Floor primary, can do Tills
        EmployeeDepartments(employee_id=100003, department_id=100002, is_primary=True),
        EmployeeDepartments(employee_id=100003, department_id=100001, is_primary=False),
        
        # Carol - CS primary (evening keyholder)
        EmployeeDepartments(employee_id=100004, department_id=100003, is_primary=True),
        EmployeeDepartments(employee_id=100004, department_id=100001, is_primary=False),
        
        # David - CS primary, can do Tills
        EmployeeDepartments(employee_id=100005, department_id=100003, is_primary=True),
        EmployeeDepartments(employee_id=100005, department_id=100001, is_primary=False),
        
        # Emma - Tills primary (morning keyholder)
        EmployeeDepartments(employee_id=100006, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100006, department_id=100002, is_primary=False),
        
        # Frank - Tills primary, flexible across all
        EmployeeDepartments(employee_id=100007, department_id=100001, is_primary=True),
        EmployeeDepartments(employee_id=100007, department_id=100002, is_primary=False),
        EmployeeDepartments(employee_id=100007, department_id=100003, is_primary=False),
    ]
    
    for link in links:
        db.add(link)
    db.commit()
    print(f"Seeded {len(links)} employee-department links.")


def seed_availability_rules(db):
    """Seed availability rules - simplified with good coverage."""
    print("Seeding availability rules...")
    
    rules = []
    rule_id = 100001
    
    # Manager (100001) - Available all week 6am-22pm (no rules = default available)
    # No rules needed - default available
    
    # Alice (100002) - Keyholder, available Mon-Fri 7am-17pm, Sat 8am-14pm
    for day in range(5):  # Mon-Fri
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100002, day_of_week=day,
            start_time_local=time(7, 0), end_time_local=time(17, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    rules.append(AvailabilityRules(
        id=rule_id, employee_id=100002, day_of_week=5,  # Sat
        start_time_local=time(8, 0), end_time_local=time(14, 0),
        rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
    ))
    rule_id += 1
    rules.append(AvailabilityRules(
        id=rule_id, employee_id=100002, day_of_week=6,  # Sun unavailable
        start_time_local=None, end_time_local=None,
        rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True
    ))
    rule_id += 1
    
    # Bob (100003) - Regular, available Mon-Sat 8am-18pm
    for day in range(6):  # Mon-Sat
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100003, day_of_week=day,
            start_time_local=time(8, 0), end_time_local=time(18, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    rules.append(AvailabilityRules(
        id=rule_id, employee_id=100003, day_of_week=6,  # Sun unavailable
        start_time_local=None, end_time_local=None,
        rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True
    ))
    rule_id += 1
    
    # Carol (100004) - Keyholder, evening specialist, available all week 13pm-22pm
    for day in range(7):
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100004, day_of_week=day,
            start_time_local=time(13, 0), end_time_local=time(22, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    
    # David (100005) - Regular, available Mon-Fri 9am-18pm
    for day in range(5):  # Mon-Fri
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100005, day_of_week=day,
            start_time_local=time(9, 0), end_time_local=time(18, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    for day in range(5, 7):  # Sat-Sun unavailable
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100005, day_of_week=day,
            start_time_local=None, end_time_local=None,
            rule_type=AvailabilityRuleType.UNAVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    
    # Emma (100006) - Keyholder, morning specialist, available all week 6am-15pm
    for day in range(7):
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100006, day_of_week=day,
            start_time_local=time(6, 0), end_time_local=time(15, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    
    # Frank (100007) - Keyholder, flexible, available all week 6am-22pm
    for day in range(7):
        rules.append(AvailabilityRules(
            id=rule_id, employee_id=100007, day_of_week=day,
            start_time_local=time(6, 0), end_time_local=time(22, 0),
            rule_type=AvailabilityRuleType.AVAILABLE, priority=1, active=True
        ))
        rule_id += 1
    
    for rule in rules:
        db.add(rule)
    db.commit()
    print(f"Seeded {len(rules)} availability rules.")


def seed_shifts(db):
    """No existing shifts - clean slate for solver."""
    print("Seeding shifts... (none - clean slate)")
    print("Seeded 0 shifts.")


def seed_time_off_requests(db):
    """No time off requests for simplicity."""
    print("Seeding time off requests... (none)")
    print("Seeded 0 time off requests.")


def seed_coverage_requirements(db):
    """Seed simplified coverage requirements."""
    print("Seeding coverage requirements...")
    
    requirements = []
    req_id = 100001
    
    # Tills: 10am-16pm daily, min 2 staff
    for day in range(7):
        requirements.append(CoverageRequirements(
            id=req_id,
            store_id=100001,
            department_id=100001,  # Tills
            day_of_week=day,
            start_time_local=time(10, 0),
            end_time_local=time(16, 0),
            min_staff=2,
            max_staff=3,
            active=True,
            last_modified_by_user_id=100001,
        ))
        req_id += 1
    
    # CS: 9am-17pm Mon-Fri only, min 1 staff
    for day in range(5):  # Mon-Fri
        requirements.append(CoverageRequirements(
            id=req_id,
            store_id=100001,
            department_id=100003,  # CS
            day_of_week=day,
            start_time_local=time(9, 0),
            end_time_local=time(17, 0),
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
    """Seed simplified role requirements - narrower windows."""
    print("Seeding role requirements...")
    
    requirements = [
        # Keyholder needed 7am-10am (opening) - narrower than 6-10
        RoleRequirements(
            id=100001,
            store_id=100001,
            department_id=None,  # Whole store
            day_of_week=None,  # Every day
            start_time_local=time(7, 0),
            end_time_local=time(10, 0),
            requires_manager=False,
            requires_keyholder=True,
            min_manager_count=0,
            active=True,
            last_modified_by_user_id=100001,
        ),
        # Keyholder needed 17pm-21pm (closing) - narrower than 18-22
        RoleRequirements(
            id=100002,
            store_id=100001,
            department_id=None,
            day_of_week=None,
            start_time_local=time(17, 0),
            end_time_local=time(21, 0),
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
    """Seed labour budgets."""
    print("Seeding labour budgets...")
    
    monday = get_current_week_monday()
    next_monday = monday + timedelta(days=7)
    
    budgets = [
        LabourBudgets(id=100001, store_id=100001, department_id=100001, week_start_date=monday, budget_hours=80),
        LabourBudgets(id=100002, store_id=100001, department_id=100002, week_start_date=monday, budget_hours=40),
        LabourBudgets(id=100003, store_id=100001, department_id=100003, week_start_date=monday, budget_hours=40),
        LabourBudgets(id=100004, store_id=100001, department_id=100001, week_start_date=next_monday, budget_hours=80),
        LabourBudgets(id=100005, store_id=100001, department_id=100002, week_start_date=next_monday, budget_hours=40),
        LabourBudgets(id=100006, store_id=100001, department_id=100003, week_start_date=next_monday, budget_hours=40),
    ]
    
    for budget in budgets:
        db.add(budget)
    db.commit()
    print(f"Seeded {len(budgets)} labour budgets.")


def main():
    """Main seed function."""
    print("\n" + "="*50)
    print("ShiftPilot Database Seeder (v4 - Simplified)")
    print("="*50 + "\n")
    
    response = input("This will DELETE ALL EXISTING DATA (except alembic versions). Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    
    db = SessionLocal()
    
    try:
        truncate_tables(db)
        
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
        
        reset_sequences(db)
        
        print("\n" + "="*50)
        print("Seeding complete!")
        print("="*50)
        print("\nTest accounts:")
        print("  Admin:    admin@shiftpilot.com / admin123")
        print("  Manager:  manager1@shiftpilot.com / manager123")
        print("  Employee: employee1@shiftpilot.com / employee123")
        print("            (employees 2-6 follow same pattern)")
        print("\nEmployee summary:")
        print("  100001 - Manager (40h, all depts, keyholder)")
        print("  100002 - Alice (32h, Tills, keyholder, Mon-Sat)")
        print("  100003 - Bob (24h, Shop Floor, regular, Mon-Sat)")
        print("  100004 - Carol (24h, CS, keyholder, evenings 13-22)")
        print("  100005 - David (24h, CS, regular, Mon-Fri 9-18)")
        print("  100006 - Emma (32h, Tills, keyholder, mornings 6-15)")
        print("  100007 - Frank (32h, Tills, keyholder, flexible 6-22)")
        print("\nTotal contracted hours: 208h/week")
        print("="*50 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()