# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShiftPilot is an AI-assisted shift scheduling application for retail stores. It has two independent apps:
- **backend/** — FastAPI + PostgreSQL + SQLAlchemy
- **frontend/** — React + TypeScript + Vite + Tailwind + shadcn/ui (Radix)

## Development Commands

### Backend
```bash
cd backend

# Run the API server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/scheduling/test_solver.py -v

# Run a specific test function
pytest tests/scheduling/test_solver.py::test_basic_coverage -v

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Seed data
python scripts/seed_data_v4.py
```

### Frontend
```bash
cd frontend

npm run dev      # Dev server on http://localhost:5173
npm run build    # TypeScript check + Vite build
npm run preview  # Preview production build
```

### Environment
Backend requires a `.env` file in `backend/` with:
```
SECRET_KEY=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=
DATABASE_URL=postgresql://user:pass@host:port/db
GEMINI_API_KEY=
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
```

## Architecture

### API Proxy
The Vite dev server proxies `/api/*` → `http://localhost:8000/api/v1/*` (rewriting the path). All frontend API calls use the path prefix `/api/` (no `v1`). In production, the same rewrite must be configured.

### Role Model
Three roles: `ADMIN`, `MANAGER`, `EMPLOYEE` (enum in `user_roles` table). A global admin has `store_id=NULL` and can access all stores. Store-scoped managers/admins are tied to a specific `store_id`. Role checks are done via dependency functions in `backend/app/api/deps.py` — use `require_admin`, `require_manager_or_admin`, `StoreAccessChecker`, etc.

### Database Models (`backend/app/db/models/`)
Key relationships:
- `Users` → 1:1 `Employees` (via `user_id`). Not all users have an employee record (pure admins).
- `Employees` → many `EmployeeDepartments` (many-to-many with `Departments`)
- `Employees` → many `AvailabilityRules`, `Shifts`, `TimeOffRequests`
- `Stores` → many `StoreDepartments` → `Departments`
- `CoverageRequirements` and `RoleRequirements` are per-store/department constraints that drive schedule generation

All soft-deletable records use an `active: bool` column rather than hard deletes.

### AI Pipeline (`backend/app/services/ai/`)
Flow when a user submits a natural-language request:
1. `AIInputs` record created via POST `/ai-inputs`
2. `process_ai_input()` in `ai_service.py` orchestrates the flow:
   - Loads context (employee info, store info, coverage rules) from DB
   - Builds system/user prompts via `prompts.py`
   - Calls `GeminiProvider.generate_json()` (REST API, no SDK — avoids protobuf conflicts)
   - Creates `AIOutputs` record with the parsed JSON result
   - Creates `AIProposals` record with `status=PENDING`
3. Manager/admin reviews proposals via `ProposalReview` page
4. On approval, `apply_proposal()` in `approval_handler.py` writes changes to constraint tables (`AvailabilityRules`, `CoverageRequirements`, `RoleRequirements`)
5. Conflict resolution for overlapping availability rules is handled in `_resolve_conflicts()` — it trims, splits, or deactivates existing rules

Both AI-generated and manual proposals go through the same `AIProposals` table. Manual proposals use `source=MANUAL` and store changes in `changes_json` instead of via `AIOutputs`.

### Schedule Solver (`backend/app/services/scheduling/`)
The active solver is `or_solver.py`, which uses **OR-Tools CP-SAT**. `generator.py` calls `or_solve_schedule` from it. The older greedy `solver.py` still exists but is no longer invoked.

**OR-Tools CP-SAT approach (`or_solver.py`):**
- Decision variables: `BoolVar` per `(employee, day, start_slot, shift_length, department)` combination — only created for slots where the employee is available
- Hard constraints: one shift per day per employee, 12-hour rest between consecutive days
- All other constraints are **soft** (weighted objective terms): coverage requirements (`-1000` per unmet slot), role requirements (`-1000` per unmet slot), contracted hours shortfall (`-100` per hour), overtime (`-3` per hour), department/availability preferences (bonuses)
- Time is discretised into 1-hour slots (6am–10pm = 16 slots/day); `SLOT_DURATION_MINUTES = 60` — a note in the code flags that 30-min granularity may be needed for more complex constraints
- Solver time limit: 120 seconds; returns `FEASIBLE` with a warning if the optimal isn't found in time

**Greedy solver (`solver.py`) — not used in production:**
Phases: cover requirements → satisfy role requirements (extending existing shifts) → fill contracted hours → retry gaps.

Internal types (`types.py`) are plain dataclasses, decoupled from SQLAlchemy models. `data_loader.py` bridges DB models → solver types.

### Frontend Auth
JWT stored in `localStorage` as `access_token`. `AuthContext` loads user, roles, and employee record on mount. `ProtectedRoute` accepts `requireManagerOrAdmin` prop to gate manager-only pages. The `useAuth()` hook exposes `isAdmin`, `isManager`, `isManagerOrAdmin`, `highestRole`.

### Frontend API Layer
All API calls go through a single axios instance in `frontend/src/services/api.ts`. It auto-injects the JWT header and redirects to `/login` on 401. Named API objects (`authApi`, `meApi`, `aiInputsApi`, `aiProposalsApi`, etc.) group related endpoints.

### Frontend Path Aliases
`@/` resolves to `frontend/src/` (configured in both `vite.config.ts` and `tsconfig.json`).

## Important Development Rules

### Solver
- `or_solver.py` is the only active solver — do NOT use or regress to `solver.py` (greedy solver is deprecated)
- 30-minute slot granularity is a known future consideration — do not implement unless explicitly asked

### AI / Gemini
- `GeminiProvider.generate_json()` is rate-limit sensitive — avoid repeated calls during testing
- Gemini API uses REST directly (no SDK) to avoid protobuf conflicts — do not switch to SDK

### General
- Incremental commits only — avoid large sweeping changes across multiple files
- All soft deletes use `active: bool` — never hard delete records
- Store-scoped access must always be enforced — managers operate within their `store_id` only
- Permission checks live in `backend/app/api/deps.py` — do not inline permission logic in routes