"""
Seed script for ShiftPilot — comprehensive demo dataset (v5)

3 stores, 6 departments, 29 employees (inc. 1 on leave), 3 managers, 1 global admin.
3 weeks of PUBLISHED/MANUAL shifts for stores 1 and 2 (09/03/2026–29/03/2026).
Store 3 is intentionally under-staffed (min_staff=3, only 2 employees).

Run with: python -m scripts.seed_data_v5
"""

import sys
from datetime import date, time, datetime, timedelta
from sqlalchemy import text
from app.db.database import SessionLocal
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
from app.db.models.coverage_requirements import CoverageRequirements
from app.db.models.role_requirements import RoleRequirements


# ── Constants ─────────────────────────────────────────────────────────────────

WEEK1_START = date(2026, 3, 9)   # Monday 09/03/2026
NUM_WEEKS = 3

# IDs — block 200xxx avoids collisions with any existing auto-generated records
U = {  # User IDs
    "admin":     200001,
    "sarah":     200002,
    "james":     200003,
    "emily":     200004,
    "michael":   200005,
    "jessica":   200006,
    "daniel":    200007,
    "sophie":    200008,
    "charlotte": 200009,
    "harry":     200010,
    "ryan":      200011,
    "emma":      200012,
    "callum":    200013,
    "priya":     200014,
    "tom":       200015,
    "grace":     200016,
    "oliver":    200017,
    "david":     200018,
    "mia":       200019,
    "ethan":     200020,
    "amelia":    200021,
    "noah":      200022,
    "isabella":  200023,
    "liam":      200024,
    "alex":      200025,
    "sam":       200026,
    # Store 1 — additional employees (fix weekend Shop Floor + Sunday Tills coverage)
    "zoe":       200027,  # Shop Floor, 32h, weekend-capable keyholder
    "jake":      200028,  # Shop Floor, 24h, Wed-Sun focused
    "lily":      200029,  # Tills, 24h, Thu-Sun focused
    "ben":       200030,  # Tills, 20h, Wed-Sun focused
}

S = {"london": 200001, "manchester": 200002, "bristol": 200003}

D = {
    "tills":     200001,
    "shopfloor": 200002,
    "freshfood": 200003,
    "cs":        200004,
    "retail":    200005,
    "warehouse": 200006,
}

E = {  # Employee IDs — same order as users minus admin
    "sarah":     200001,
    "james":     200002,
    "emily":     200003,
    "michael":   200004,
    "jessica":   200005,
    "daniel":    200006,
    "sophie":    200007,
    "charlotte": 200008,
    "harry":     200009,
    "ryan":      200010,
    "emma":      200011,
    "callum":    200012,
    "priya":     200013,
    "tom":       200014,
    "grace":     200015,
    "oliver":    200016,
    "david":     200017,
    "mia":       200018,
    "ethan":     200019,
    "amelia":    200020,
    "noah":      200021,
    "isabella":  200022,
    "liam":      200023,
    "alex":      200024,
    "sam":       200025,
    "zoe":       200026,
    "jake":      200027,
    "lily":      200028,
    "ben":       200029,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def truncate_tables(db):
    print("Truncating tables...")
    tables = [
        "role_requirements",
        "coverage_requirements",
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
    for table in tables:
        db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
    db.commit()
    print("All tables truncated.")


def reset_sequences(db):
    print("Resetting sequences...")
    sequences = [
        ("users",                  "users_id_seq"),
        ("stores",                 "stores_id_seq"),
        ("departments",            "departments_id_seq"),
        ("employees",              "employees_id_seq"),
        ("user_roles",             "user_roles_id_seq"),
        ("availability_rules",     "availability_rules_id_seq"),
        ("shifts",                 "shifts_id_seq"),
        ("coverage_requirements",  "coverage_requirements_id_seq"),
        ("role_requirements",      "role_requirements_id_seq"),
    ]
    for table, seq in sequences:
        db.execute(text(
            f"SELECT setval('{seq}', (SELECT COALESCE(MAX(id), 1) FROM {table}));"
        ))
    db.commit()
    print("Sequences reset.")


# ── Users ─────────────────────────────────────────────────────────────────────

def seed_users(db):
    print("Seeding users...")
    pw_admin    = get_password_hash("admin123")
    pw_manager  = get_password_hash("manager123")
    pw_employee = get_password_hash("employee123")

    users = [
        Users(id=U["admin"],     email="admin@shiftpilot.work",         firstname="Admin",     surname="User",      password_hash=pw_admin,    is_active=True),
        # Store 1
        Users(id=U["sarah"],     email="sarah.johnson@shiftpilot.work",  firstname="Sarah",     surname="Johnson",   password_hash=pw_manager,  is_active=True),
        Users(id=U["james"],     email="james.wilson@shiftpilot.work",   firstname="James",     surname="Wilson",    password_hash=pw_employee, is_active=True),
        Users(id=U["emily"],     email="emily.davis@shiftpilot.work",    firstname="Emily",     surname="Davis",     password_hash=pw_employee, is_active=True),
        Users(id=U["michael"],   email="michael.brown@shiftpilot.work",  firstname="Michael",   surname="Brown",     password_hash=pw_employee, is_active=True),
        Users(id=U["jessica"],   email="jessica.taylor@shiftpilot.work", firstname="Jessica",   surname="Taylor",    password_hash=pw_employee, is_active=True),
        Users(id=U["daniel"],    email="daniel.martinez@shiftpilot.work",firstname="Daniel",    surname="Martinez",  password_hash=pw_employee, is_active=True),
        Users(id=U["sophie"],    email="sophie.anderson@shiftpilot.work",firstname="Sophie",    surname="Anderson",  password_hash=pw_employee, is_active=True),
        Users(id=U["charlotte"], email="charlotte.jackson@shiftpilot.work",firstname="Charlotte",surname="Jackson",  password_hash=pw_employee, is_active=True),
        Users(id=U["harry"],     email="harry.white@shiftpilot.work",    firstname="Harry",     surname="White",     password_hash=pw_employee, is_active=True),
        Users(id=U["ryan"],      email="ryan.cooper@shiftpilot.work",    firstname="Ryan",      surname="Cooper",    password_hash=pw_employee, is_active=True),
        Users(id=U["emma"],      email="emma.clarke@shiftpilot.work",    firstname="Emma",      surname="Clarke",    password_hash=pw_employee, is_active=True),
        Users(id=U["callum"],    email="callum.hughes@shiftpilot.work",  firstname="Callum",    surname="Hughes",    password_hash=pw_employee, is_active=True),
        Users(id=U["priya"],     email="priya.patel@shiftpilot.work",    firstname="Priya",     surname="Patel",     password_hash=pw_employee, is_active=True),
        Users(id=U["tom"],       email="tom.bennett@shiftpilot.work",    firstname="Tom",       surname="Bennett",   password_hash=pw_employee, is_active=True),
        Users(id=U["grace"],     email="grace.mitchell@shiftpilot.work", firstname="Grace",     surname="Mitchell",  password_hash=pw_employee, is_active=True),
        Users(id=U["oliver"],    email="oliver.thomas@shiftpilot.work",  firstname="Oliver",    surname="Thomas",    password_hash=pw_employee, is_active=True),
        # Store 2
        Users(id=U["david"],     email="david.roberts@shiftpilot.work",  firstname="David",     surname="Roberts",   password_hash=pw_manager,  is_active=True),
        Users(id=U["mia"],       email="mia.thompson@shiftpilot.work",   firstname="Mia",       surname="Thompson",  password_hash=pw_employee, is_active=True),
        Users(id=U["ethan"],     email="ethan.garcia@shiftpilot.work",   firstname="Ethan",     surname="Garcia",    password_hash=pw_employee, is_active=True),
        Users(id=U["amelia"],    email="amelia.harris@shiftpilot.work",  firstname="Amelia",    surname="Harris",    password_hash=pw_employee, is_active=True),
        Users(id=U["noah"],      email="noah.clark@shiftpilot.work",     firstname="Noah",      surname="Clark",     password_hash=pw_employee, is_active=True),
        Users(id=U["isabella"],  email="isabella.lewis@shiftpilot.work", firstname="Isabella",  surname="Lewis",     password_hash=pw_employee, is_active=True),
        Users(id=U["liam"],      email="liam.walker@shiftpilot.work",    firstname="Liam",      surname="Walker",    password_hash=pw_employee, is_active=True),
        # Store 3
        Users(id=U["alex"],      email="alex.reed@shiftpilot.work",      firstname="Alex",      surname="Reed",      password_hash=pw_manager,  is_active=True),
        Users(id=U["sam"],       email="sam.price@shiftpilot.work",      firstname="Sam",       surname="Price",     password_hash=pw_employee, is_active=True),
        # Store 1 — additional employees
        Users(id=U["zoe"],       email="zoe.parker@shiftpilot.work",     firstname="Zoe",       surname="Parker",    password_hash=pw_employee, is_active=True),
        Users(id=U["jake"],      email="jake.morris@shiftpilot.work",    firstname="Jake",      surname="Morris",    password_hash=pw_employee, is_active=True),
        Users(id=U["lily"],      email="lily.evans@shiftpilot.work",     firstname="Lily",      surname="Evans",     password_hash=pw_employee, is_active=True),
        Users(id=U["ben"],       email="ben.clarke@shiftpilot.work",     firstname="Ben",       surname="Clarke",    password_hash=pw_employee, is_active=True),
    ]
    for u in users:
        db.add(u)
    db.commit()
    print(f"Seeded {len(users)} users.")


# ── Stores ────────────────────────────────────────────────────────────────────

def seed_stores(db):
    print("Seeding stores...")
    stores = [
        Stores(id=S["london"],     name="ShiftPilot Metro London",   location="Oxford Street, London",  timezone="Europe/London", opening_time=time(7,0),  closing_time=time(22,0)),
        Stores(id=S["manchester"], name="ShiftPilot Express Manchester", location="Piccadilly, Manchester", timezone="Europe/London", opening_time=time(6,0),  closing_time=time(23,0)),
        Stores(id=S["bristol"],    name="ShiftPilot Dark Bristol",    location="Clifton, Bristol",       timezone="Europe/London", opening_time=time(8,0),  closing_time=time(20,0)),
    ]
    for s in stores:
        db.add(s)
    db.commit()
    print(f"Seeded {len(stores)} stores.")


# ── Departments ───────────────────────────────────────────────────────────────

def seed_departments(db):
    print("Seeding departments...")
    depts = [
        Departments(id=D["tills"],     name="Tills",            code="TILLS",     has_manager_role=False),
        Departments(id=D["shopfloor"], name="Shop Floor",       code="SHOPFLOOR", has_manager_role=True),
        Departments(id=D["freshfood"], name="Fresh Food",       code="FRESHFOOD", has_manager_role=False),
        Departments(id=D["cs"],        name="Customer Service", code="CS",        has_manager_role=True),
        Departments(id=D["retail"],    name="Retail",           code="RETAIL",    has_manager_role=True),
        Departments(id=D["warehouse"], name="Warehouse",        code="WAREHOUSE", has_manager_role=False),
    ]
    for d in depts:
        db.add(d)
    db.commit()
    print(f"Seeded {len(depts)} departments.")


# ── Store-Department links ────────────────────────────────────────────────────

def seed_store_departments(db):
    print("Seeding store-department links...")
    links = [
        # Store 1 — London
        StoreDepartment(store_id=S["london"], department_id=D["tills"]),
        StoreDepartment(store_id=S["london"], department_id=D["shopfloor"]),
        StoreDepartment(store_id=S["london"], department_id=D["freshfood"]),
        StoreDepartment(store_id=S["london"], department_id=D["cs"]),
        # Store 2 — Manchester
        StoreDepartment(store_id=S["manchester"], department_id=D["retail"]),
        StoreDepartment(store_id=S["manchester"], department_id=D["warehouse"]),
        # Store 3 — Bristol
        StoreDepartment(store_id=S["bristol"], department_id=D["retail"]),
    ]
    for l in links:
        db.add(l)
    db.commit()
    print(f"Seeded {len(links)} store-department links.")


# ── User Roles ────────────────────────────────────────────────────────────────

def seed_user_roles(db):
    print("Seeding user roles...")
    rid = 200001

    def role(user_key, role_enum, store_key=None):
        nonlocal rid
        r = UserRoles(id=rid, user_id=U[user_key], store_id=S[store_key] if store_key else None, role=role_enum)
        rid += 1
        return r

    roles = [
        role("admin",     Role.ADMIN),
        # Store 1
        role("sarah",     Role.MANAGER,  "london"),
        role("sarah",     Role.EMPLOYEE, "london"),
        role("james",     Role.EMPLOYEE, "london"),
        role("emily",     Role.EMPLOYEE, "london"),
        role("michael",   Role.EMPLOYEE, "london"),
        role("jessica",   Role.EMPLOYEE, "london"),
        role("daniel",    Role.EMPLOYEE, "london"),
        role("sophie",    Role.EMPLOYEE, "london"),
        role("charlotte", Role.EMPLOYEE, "london"),
        role("harry",     Role.EMPLOYEE, "london"),
        role("ryan",      Role.EMPLOYEE, "london"),
        role("emma",      Role.EMPLOYEE, "london"),
        role("callum",    Role.EMPLOYEE, "london"),
        role("priya",     Role.EMPLOYEE, "london"),
        role("tom",       Role.EMPLOYEE, "london"),
        role("grace",     Role.EMPLOYEE, "london"),
        role("oliver",    Role.EMPLOYEE, "london"),
        # Store 2
        role("david",     Role.MANAGER,  "manchester"),
        role("david",     Role.EMPLOYEE, "manchester"),
        role("mia",       Role.EMPLOYEE, "manchester"),
        role("ethan",     Role.EMPLOYEE, "manchester"),
        role("amelia",    Role.EMPLOYEE, "manchester"),
        role("noah",      Role.EMPLOYEE, "manchester"),
        role("isabella",  Role.EMPLOYEE, "manchester"),
        role("liam",      Role.EMPLOYEE, "manchester"),
        # Store 3
        role("alex",      Role.MANAGER,  "bristol"),
        role("alex",      Role.EMPLOYEE, "bristol"),
        role("sam",       Role.EMPLOYEE, "bristol"),
        # Store 1 — additional
        role("zoe",       Role.EMPLOYEE, "london"),
        role("jake",      Role.EMPLOYEE, "london"),
        role("lily",      Role.EMPLOYEE, "london"),
        role("ben",       Role.EMPLOYEE, "london"),
    ]
    for r in roles:
        db.add(r)
    db.commit()
    print(f"Seeded {len(roles)} user roles.")


# ── Employees ─────────────────────────────────────────────────────────────────

def seed_employees(db):
    print("Seeding employees...")

    def emp(key, user_key, store_key, hours, dob, keyholder=False, manager=False, status=EmploymentStatus.ACTIVE):
        return Employees(
            id=E[key],
            user_id=U[user_key],
            store_id=S[store_key],
            contracted_weekly_hours=hours,
            dob=dob,
            is_keyholder=keyholder,
            is_manager=manager,
            employment_status=status,
        )

    employees = [
        # Store 1
        emp("sarah",     "sarah",     "london",     40,   date(1985, 6, 14), keyholder=True, manager=True),
        emp("james",     "james",     "london",     37.5, date(1990, 2, 23), keyholder=True),
        emp("emily",     "emily",     "london",     37.5, date(1993, 9, 11), keyholder=True),
        emp("michael",   "michael",   "london",     24,   date(1999, 4,  5)),
        emp("jessica",   "jessica",   "london",     20,   date(2001, 8, 30)),
        emp("daniel",    "daniel",    "london",     16,   date(2003, 1, 17)),
        emp("sophie",    "sophie",    "london",     32,   date(1996, 12, 3), keyholder=True),
        emp("charlotte", "charlotte", "london",     24,   date(2000, 7, 22)),
        emp("harry",     "harry",     "london",     16,   date(2004, 3, 19)),
        emp("ryan",      "ryan",      "london",     20,   date(2002, 10, 8)),
        emp("emma",      "emma",      "london",     30,   date(1997, 5, 27), keyholder=True),
        emp("callum",    "callum",    "london",     24,   date(2001, 11, 14)),
        emp("priya",     "priya",     "london",     16,   date(2003, 6, 2)),
        emp("tom",       "tom",       "london",     20,   date(1998, 3, 31)),
        emp("grace",     "grace",     "london",     24,   date(2000, 9, 18)),
        emp("oliver",    "oliver",    "london",     20,   date(1999, 1, 25), status=EmploymentStatus.ON_LEAVE),
        # Store 2
        emp("david",     "david",     "manchester", 40,   date(1983, 7, 10), keyholder=True, manager=True),
        emp("mia",       "mia",       "manchester", 37.5, date(1994, 4, 16), keyholder=True),
        emp("ethan",     "ethan",     "manchester", 37.5, date(1992, 11, 29), keyholder=True),
        emp("amelia",    "amelia",    "manchester", 24,   date(1998, 8,  3)),
        emp("noah",      "noah",      "manchester", 16,   date(2002, 5, 21)),
        emp("isabella",  "isabella",  "manchester", 20,   date(2001, 2, 14), keyholder=True),
        emp("liam",      "liam",      "manchester", 16,   date(2003, 9,  7)),
        # Store 3
        emp("alex",      "alex",      "bristol",    37.5, date(1988, 4, 30), keyholder=True, manager=True),
        emp("sam",       "sam",       "bristol",    16,   date(2004, 12, 1)),
        # Store 1 — additional (19 active total)
        emp("zoe",       "zoe",       "london",     32,   date(1996, 7, 14), keyholder=True),
        emp("jake",      "jake",      "london",     24,   date(2000, 3, 22)),
        emp("lily",      "lily",      "london",     24,   date(2001, 9, 5)),
        emp("ben",       "ben",       "london",     20,   date(2002, 11, 18)),
    ]
    for e in employees:
        db.add(e)
    db.commit()
    print(f"Seeded {len(employees)} employees.")


# ── Employee-Department links ─────────────────────────────────────────────────

def seed_employee_departments(db):
    print("Seeding employee-department links...")

    def link(emp_key, dept_key, primary=False):
        return EmployeeDepartments(employee_id=E[emp_key], department_id=D[dept_key], is_primary=primary)

    links = [
        # Store 1
        link("sarah",     "tills",     primary=True),
        link("sarah",     "cs"),
        link("sarah",     "shopfloor"),
        link("sarah",     "freshfood"),

        link("james",     "tills",     primary=True),
        link("james",     "shopfloor"),

        link("emily",     "tills",     primary=True),
        link("emily",     "freshfood"),

        link("michael",   "shopfloor", primary=True),

        link("jessica",   "cs",        primary=True),

        link("daniel",    "tills",     primary=True),

        link("sophie",    "freshfood", primary=True),
        link("sophie",    "shopfloor"),

        link("charlotte", "tills",     primary=True),
        link("charlotte", "cs"),

        link("harry",     "shopfloor", primary=True),

        link("ryan",      "shopfloor", primary=True),

        link("emma",      "tills",     primary=True),
        link("emma",      "shopfloor"),

        link("callum",    "shopfloor", primary=True),
        link("callum",    "freshfood"),

        link("priya",     "cs",        primary=True),
        link("priya",     "tills"),

        link("tom",       "freshfood", primary=True),

        link("grace",     "tills",     primary=True),
        link("grace",     "cs"),

        link("oliver",    "shopfloor", primary=True),
        link("oliver",    "cs"),

        # Store 2
        link("david",     "retail",    primary=True),
        link("david",     "warehouse"),

        link("mia",       "retail",    primary=True),
        link("mia",       "warehouse"),

        link("ethan",     "retail",    primary=True),

        link("amelia",    "retail",    primary=True),

        link("noah",      "warehouse", primary=True),

        link("isabella",  "retail",    primary=True),

        link("liam",      "retail",    primary=True),
        link("liam",      "warehouse"),

        # Store 3
        link("alex",      "retail",    primary=True),
        link("sam",       "retail",    primary=True),

        # Store 1 — additional
        link("zoe",       "shopfloor", primary=True),
        link("zoe",       "tills"),

        link("jake",      "shopfloor", primary=True),

        link("lily",      "tills",     primary=True),
        link("lily",      "cs"),

        link("ben",       "tills",     primary=True),
        link("ben",       "shopfloor"),
    ]
    for l in links:
        db.add(l)
    db.commit()
    print(f"Seeded {len(links)} employee-department links.")


# ── Availability Rules ────────────────────────────────────────────────────────

def seed_availability_rules(db):
    print("Seeding availability rules...")
    rules = []
    rid = 200001

    def avail(emp_key, dow, start_h, start_m, end_h, end_m):
        nonlocal rid
        r = AvailabilityRules(
            id=rid, employee_id=E[emp_key], day_of_week=dow,
            start_time_local=time(start_h, start_m),
            end_time_local=time(end_h, end_m),
            rule_type=AvailabilityRuleType.AVAILABLE,
            priority=1, active=True,
        )
        rid += 1
        return r

    def unavail(emp_key, dow):
        nonlocal rid
        r = AvailabilityRules(
            id=rid, employee_id=E[emp_key], day_of_week=dow,
            start_time_local=None, end_time_local=None,
            rule_type=AvailabilityRuleType.UNAVAILABLE,
            priority=1, active=True,
        )
        rid += 1
        return r

    # Managers — AVAILABLE Mon-Sun 06:00-22:00
    for key in ("sarah", "david", "alex"):
        for dow in range(7):
            rules.append(avail(key, dow, 6, 0, 22, 0))

    # Keyholders — AVAILABLE Mon-Sun 06:00-22:00
    for key in ("emily", "mia", "ethan"):
        for dow in range(7):
            rules.append(avail(key, dow, 6, 0, 22, 0))

    # James — AVAILABLE Mon-Sat, UNAVAILABLE Sun
    for dow in range(6):
        rules.append(avail("james", dow, 6, 0, 22, 0))
    rules.append(unavail("james", 6))

    # Sophie — AVAILABLE Mon-Sat, UNAVAILABLE Sun
    for dow in range(6):
        rules.append(avail("sophie", dow, 6, 0, 22, 0))
    rules.append(unavail("sophie", 6))

    # Emma — AVAILABLE Mon-Sun 06:00-22:00 (keyholder, no restriction)
    for dow in range(7):
        rules.append(avail("emma", dow, 6, 0, 22, 0))

    # Jessica — UNAVAILABLE Sat, Sun (weekdays only)
    for dow in (5, 6):
        rules.append(unavail("jessica", dow))

    # Daniel — UNAVAILABLE Mon, Tue (Wed-Sun only)
    for dow in (0, 1):
        rules.append(unavail("daniel", dow))

    # Charlotte — UNAVAILABLE Sun
    rules.append(unavail("charlotte", 6))

    # Tom — UNAVAILABLE Sat only (can work Sunday Fresh Food to cover Sophie's day off)
    rules.append(unavail("tom", 5))

    # Callum — UNAVAILABLE Fri, Sat, Sun (Mon-Thu only)
    for dow in (4, 5, 6):
        rules.append(unavail("callum", dow))

    # Grace — UNAVAILABLE Tue, Thu
    for dow in (1, 3):
        rules.append(unavail("grace", dow))

    # Harry — UNAVAILABLE Mon, Tue, Wed (weekend-focused, Thu-Sun)
    # Keeps his 16h contracted budget free for the Shop Floor weekend requirement
    for dow in (0, 1, 2):
        rules.append(unavail("harry", dow))

    # Ryan — UNAVAILABLE Mon, Tue (available Wed-Sun, focused on Fri-Sun weekends)
    # Keeps his 20h contracted budget free for weekend Shop Floor coverage
    for dow in (0, 1):
        rules.append(unavail("ryan", dow))

    # Zoe — AVAILABLE Mon-Sun 06:00-22:00 (keyholder, no restrictions)
    for dow in range(7):
        rules.append(avail("zoe", dow, 6, 0, 22, 0))

    # Jake — UNAVAILABLE Mon, Tue (Wed-Sun focused, maximises weekend Shop Floor)
    for dow in (0, 1):
        rules.append(unavail("jake", dow))

    # Lily — UNAVAILABLE Mon, Tue, Wed (Thu-Sun focused, weekend Tills coverage)
    for dow in (0, 1, 2):
        rules.append(unavail("lily", dow))

    # Ben — UNAVAILABLE Mon, Tue (Wed-Sun available, weekend Tills backup)
    for dow in (0, 1):
        rules.append(unavail("ben", dow))

    # Noah — UNAVAILABLE Sat, Sun
    for dow in (5, 6):
        rules.append(unavail("noah", dow))

    # Isabella — UNAVAILABLE Mon
    rules.append(unavail("isabella", 0))

    for r in rules:
        db.add(r)
    db.commit()
    print(f"Seeded {len(rules)} availability rules.")


# ── Coverage Requirements ─────────────────────────────────────────────────────

def seed_coverage_requirements(db):
    print("Seeding coverage requirements...")
    reqs = []
    rid = 200001

    def cov(store_key, dept_key, days, start_h, start_m, end_h, end_m, min_staff, max_staff=None):
        nonlocal rid
        if max_staff is None:
            max_staff = min_staff + 2
        for dow in days:
            reqs.append(CoverageRequirements(
                id=rid,
                store_id=S[store_key],
                department_id=D[dept_key],
                day_of_week=dow,
                start_time_local=time(start_h, start_m),
                end_time_local=time(end_h, end_m),
                min_staff=min_staff,
                max_staff=max_staff,
                active=True,
                last_modified_by_user_id=U["admin"],
            ))
            rid += 1

    WEEKDAYS  = list(range(5))    # Mon-Fri = 0-4
    WEEKENDS  = [5, 6]            # Sat-Sun
    ALL_WEEK  = list(range(7))

    # --- Store 1 London ---
    # 07:00-09:00 opening window — ensures shift vars exist before main Tills coverage starts
    cov("london", "tills",     ALL_WEEK, 7,0,9,0, min_staff=1)
    cov("london", "tills",     WEEKDAYS, 9,0,18,0, min_staff=2)
    cov("london", "tills",     WEEKDAYS, 18,0,22,0, min_staff=1)
    cov("london", "tills",     WEEKENDS, 9,0,18,0, min_staff=3)
    cov("london", "tills",     WEEKENDS, 18,0,22,0, min_staff=2)
    cov("london", "shopfloor", WEEKDAYS, 8,0,14,0, min_staff=1)  # morning slot
    cov("london", "shopfloor", WEEKDAYS, 14,0,20,0, min_staff=2)  # afternoon slot (Callum + Harry/Ryan overlap)
    # Weekend Shop Floor: split into AM/PM to allow staggered 8h shifts to satisfy coverage
    cov("london", "shopfloor", WEEKENDS, 8,0,14,0, min_staff=2)   # morning: Michael + Ryan/Harry
    cov("london", "shopfloor", WEEKENDS, 14,0,20,0, min_staff=2)  # afternoon: Harry + Ryan
    cov("london", "freshfood", ALL_WEEK, 7,0,14,0, min_staff=1)
    cov("london", "freshfood", ALL_WEEK, 14,0,20,0, min_staff=1)
    cov("london", "cs",        WEEKDAYS, 9,0,17,0, min_staff=1)
    cov("london", "cs",        [5],      10,0,16,0, min_staff=1)  # Sat only

    # --- Store 2 Manchester ---
    # 06:00-07:00 retail row forces the solver to create shift variables starting at 06:00,
    # which is required to satisfy the 06:00-09:00 opening keyholder role requirement.
    cov("manchester", "retail",    ALL_WEEK, 6,0,7,0,   min_staff=1, max_staff=2)
    cov("manchester", "retail",    WEEKDAYS, 7,0,15,0,  min_staff=2)
    cov("manchester", "retail",    WEEKDAYS, 15,0,23,0, min_staff=2)
    cov("manchester", "retail",    WEEKENDS, 7,0,15,0,  min_staff=2)
    cov("manchester", "retail",    WEEKENDS, 15,0,23,0, min_staff=2)
    cov("manchester", "warehouse", WEEKDAYS, 6,0,12,0,  min_staff=1)
    cov("manchester", "warehouse", [5],      6,0,10,0,  min_staff=1)  # Sat only

    # --- Store 3 Bristol — intentionally impossible ---
    cov("bristol", "retail", ALL_WEEK, 8,0,20,0, min_staff=3)

    for r in reqs:
        db.add(r)
    db.commit()
    print(f"Seeded {len(reqs)} coverage requirements.")


# ── Role Requirements ─────────────────────────────────────────────────────────

def seed_role_requirements(db):
    print("Seeding role requirements...")
    reqs = []
    rid = 200001

    def role_req(store_key, dow, start_h, start_m, end_h, end_m, keyholder=False, manager=False):
        nonlocal rid
        r = RoleRequirements(
            id=rid,
            store_id=S[store_key],
            department_id=None,
            day_of_week=dow,
            start_time_local=time(start_h, start_m),
            end_time_local=time(end_h, end_m),
            requires_keyholder=keyholder,
            requires_manager=manager,
            min_manager_count=1 if manager else 0,
            active=True,
            last_modified_by_user_id=U["admin"],
        )
        rid += 1
        return r

    # Store 1 — London
    for dow in range(7):
        reqs.append(role_req("london", dow, 7, 0, 10, 0, keyholder=True))   # opening keyholder
        reqs.append(role_req("london", dow, 19, 0, 22, 0, keyholder=True))  # closing keyholder
    for dow in range(5):
        reqs.append(role_req("london", dow, 9, 0, 17, 0, manager=True))     # weekday manager

    # Store 2 — Manchester
    for dow in range(7):
        reqs.append(role_req("manchester", dow, 6, 0, 9, 0, keyholder=True))   # opening
        reqs.append(role_req("manchester", dow, 20, 0, 23, 0, keyholder=True)) # closing

    # Store 3 — Bristol
    for dow in range(7):
        reqs.append(role_req("bristol", dow, 8, 0, 20, 0, keyholder=True))

    for r in reqs:
        db.add(r)
    db.commit()
    print(f"Seeded {len(reqs)} role requirements.")


# ── Shifts ────────────────────────────────────────────────────────────────────

def seed_shifts(db):
    print("Seeding shifts (3 weeks, stores 1 & 2)...")
    shifts = []
    sid = 200001

    def make_shifts_for_pattern(emp_key, store_key, dept_key, days_of_week, sh, sm, eh, em):
        """Generate shifts for given employee across all 3 weeks."""
        nonlocal sid
        for week in range(NUM_WEEKS):
            week_start = WEEK1_START + timedelta(weeks=week)
            for dow in days_of_week:
                day_date = week_start + timedelta(days=dow)
                start_dt = datetime.combine(day_date, time(sh, sm))
                end_dt   = datetime.combine(day_date, time(eh, em))
                shifts.append(Shifts(
                    id=sid,
                    employee_id=E[emp_key],
                    store_id=S[store_key],
                    department_id=D[dept_key],
                    start_datetime_utc=start_dt,
                    end_datetime_utc=end_dt,
                    status=ShiftStatus.PUBLISHED,
                    source=ShiftSource.MANUAL,
                ))
                sid += 1

    # ── Store 1 — London ──────────────────────────────────────────────────────

    # Sarah: Mon/Wed/Fri Tills 09-17, Tue/Thu CS 09-17
    make_shifts_for_pattern("sarah", "london", "tills",     [0,2,4], 9,0,17,0)
    make_shifts_for_pattern("sarah", "london", "cs",        [1,3],   9,0,17,0)

    # James: Mon-Fri Tills 07-15:30, Sat Tills 08-14
    make_shifts_for_pattern("james", "london", "tills",     [0,1,2,3,4], 7,0,15,30)
    make_shifts_for_pattern("james", "london", "tills",     [5],         8,0,14,0)

    # Emily: Mon-Fri Tills 13:30-22:00, Sat Fresh Food 08-16
    make_shifts_for_pattern("emily", "london", "tills",     [0,1,2,3,4], 13,30,22,0)
    make_shifts_for_pattern("emily", "london", "freshfood", [5],         8,0,16,0)

    # Michael: Mon-Thu Shop Floor 09-15, Sat Shop Floor 10-18
    make_shifts_for_pattern("michael", "london", "shopfloor", [0,1,2,3], 9,0,15,0)
    make_shifts_for_pattern("michael", "london", "shopfloor", [5],       10,0,18,0)

    # Jessica: Mon-Fri CS 10-14
    make_shifts_for_pattern("jessica", "london", "cs", [0,1,2,3,4], 10,0,14,0)

    # Daniel: Wed-Fri Tills 16-22, Sat-Sun Tills 10-18
    make_shifts_for_pattern("daniel", "london", "tills", [2,3,4], 16,0,22,0)
    make_shifts_for_pattern("daniel", "london", "tills", [5,6],   10,0,18,0)

    # Sophie: Mon-Sat Fresh Food 07-13
    make_shifts_for_pattern("sophie", "london", "freshfood", [0,1,2,3,4,5], 7,0,13,0)

    # Charlotte: Tue-Sat Tills 10-18
    make_shifts_for_pattern("charlotte", "london", "tills", [1,2,3,4,5], 10,0,18,0)

    # Harry: Thu-Sun Shop Floor 12-20
    make_shifts_for_pattern("harry", "london", "shopfloor", [3,4,5,6], 12,0,20,0)

    # Ryan: Fri-Sun Shop Floor 10-18
    make_shifts_for_pattern("ryan", "london", "shopfloor", [4,5,6], 10,0,18,0)

    # Emma: Mon-Wed + Sat Tills 08-14
    make_shifts_for_pattern("emma", "london", "tills", [0,1,2,5], 8,0,14,0)

    # Callum: Mon-Thu Shop Floor 12-18
    make_shifts_for_pattern("callum", "london", "shopfloor", [0,1,2,3], 12,0,18,0)

    # Priya: Wed-Fri Tills 14-18, Sat-Sun CS 10-14
    make_shifts_for_pattern("priya", "london", "tills", [2,3,4], 14,0,18,0)
    make_shifts_for_pattern("priya", "london", "cs",    [5,6],   10,0,14,0)

    # Tom: Mon-Fri Fresh Food 14-18
    make_shifts_for_pattern("tom", "london", "freshfood", [0,1,2,3,4], 14,0,18,0)

    # Grace: Mon, Wed, Fri, Sat Tills 10-16
    make_shifts_for_pattern("grace", "london", "tills", [0,2,4,5], 10,0,16,0)

    # Zoe: Tue+Wed+Sat+Sun Shop Floor 08-16 (4 × 8h = 32h)
    make_shifts_for_pattern("zoe", "london", "shopfloor", [1,2,5,6], 8,0,16,0)

    # Jake: Thu+Fri+Sat Shop Floor 08-16 (3 × 8h = 24h)
    make_shifts_for_pattern("jake", "london", "shopfloor", [3,4,5], 8,0,16,0)

    # Lily: Thu+Fri+Sat+Sun Tills 10-16 (4 × 6h = 24h)
    make_shifts_for_pattern("lily", "london", "tills", [3,4,5,6], 10,0,16,0)

    # Ben: Wed+Thu+Sat+Sun Tills 12-17 (4 × 5h = 20h)
    make_shifts_for_pattern("ben", "london", "tills", [2,3,5,6], 12,0,17,0)

    # Oliver: ON_LEAVE — no shifts

    # ── Store 2 — Manchester ──────────────────────────────────────────────────

    # David: Mon-Sat Retail 08-16:30
    make_shifts_for_pattern("david", "manchester", "retail", [0,1,2,3,4,5], 8,0,16,30)

    # Mia: Mon-Sun Retail 07-15:30
    make_shifts_for_pattern("mia", "manchester", "retail", list(range(7)), 7,0,15,30)

    # Ethan: Mon-Sun Retail 14:30-23:00
    make_shifts_for_pattern("ethan", "manchester", "retail", list(range(7)), 14,30,23,0)

    # Amelia: Mon-Thu Retail 09-15, Sat Retail 10-16
    make_shifts_for_pattern("amelia", "manchester", "retail", [0,1,2,3], 9,0,15,0)
    make_shifts_for_pattern("amelia", "manchester", "retail", [5],       10,0,16,0)

    # Noah: Mon-Fri Warehouse 06-12
    make_shifts_for_pattern("noah", "manchester", "warehouse", [0,1,2,3,4], 6,0,12,0)

    # Isabella: Tue-Sat Retail 15-20
    make_shifts_for_pattern("isabella", "manchester", "retail", [1,2,3,4,5], 15,0,20,0)

    # Liam: Wed-Sat Retail 10-16, Sun Warehouse 06-10
    make_shifts_for_pattern("liam", "manchester", "retail",    [2,3,4,5], 10,0,16,0)
    make_shifts_for_pattern("liam", "manchester", "warehouse", [6],       6,0,10,0)

    for s in shifts:
        db.add(s)
    db.commit()
    print(f"Seeded {len(shifts)} shifts.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("ShiftPilot Database Seeder — v5 (Full Demo Dataset)")
    print("=" * 60)
    print("\nThis will DELETE ALL EXISTING DATA and repopulate from scratch.")
    response = input("Continue? (yes/no): ")
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
        seed_coverage_requirements(db)
        seed_role_requirements(db)
        seed_shifts(db)

        reset_sequences(db)

        print("\n" + "=" * 60)
        print("Seeding complete!")
        print("=" * 60)
        print("""
Credentials
  Admin:      admin@shiftpilot.work       / admin123
  Manager 1:  sarah.johnson@shiftpilot.work / manager123  (London)
  Manager 2:  david.roberts@shiftpilot.work / manager123  (Manchester)
  Manager 3:  alex.reed@shiftpilot.work     / manager123  (Bristol)
  Employees:  <firstname>.<surname>@shiftpilot.work / employee123

Store summary
  London     — 19 active employees + 1 on leave (Oliver Thomas)
               Shifts: 09/03/2026 – 29/03/2026 (published)
  Manchester — 7 active employees
               Shifts: 09/03/2026 – 29/03/2026 (published)
               Note: Mia seeded 7 days/week — generating week 4 will hit the
               6-consecutive-day constraint (Monday blocked) → unmet coverage
  Bristol    — 2 employees, min_staff=3 → solver will fail (by design)
               No pre-seeded shifts
""")
    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
