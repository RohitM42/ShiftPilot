from fastapi import FastAPI
from app.api.routes import (
    auth,
    users,
    stores,
    departments,
    store_departments,
    employees,
    employee_departments,
    user_roles,
    shifts,
    availability_rules,
    time_off_requests,
    coverage_requirements,
    role_requirements,
    labour_budgets,
    me,
)

app = FastAPI(title="ShiftPilot API", version="0.1.0")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(store_departments.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(employee_departments.router, prefix="/api/v1")
app.include_router(user_roles.router, prefix="/api/v1")
app.include_router(shifts.router, prefix="/api/v1")
app.include_router(availability_rules.router, prefix="/api/v1")
app.include_router(time_off_requests.router, prefix="/api/v1")
app.include_router(coverage_requirements.router, prefix="/api/v1")
app.include_router(role_requirements.router, prefix="/api/v1")
app.include_router(labour_budgets.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}