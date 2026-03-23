# ShiftPilot

An AI-assisted shift scheduling system for retail stores. Managers can generate optimised schedules using a constraint-based solver, adjust rules through a natural language interface, and publish shifts to employees — all from a role-scoped web application.

## Features

- **Automated schedule generation** via OR-Tools CP-SAT — respects availability, contracted hours, coverage requirements, and role requirements
- **Natural language scheduling** — managers describe requirement changes in plain English, reviewed as proposals before applying
- **Three-tier role model** — Admin, Manager, and Employee views with store-scoped access control
- **Gantt schedule view** — visual day-by-day schedule with draft/published shift states
- **Proposal review workflow** — AI and manual proposals reviewed and approved before changes take effect

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, PostgreSQL, SQLAlchemy, Alembic |
| Scheduler | OR-Tools CP-SAT |
| AI | Google Gemini (via REST), OpenRouter |
| Frontend | React, TypeScript, Vite, Tailwind, shadcn/ui |

## Project Structure

```
rxm631/
├── backend/       # FastAPI app, solver, AI service, DB models
└── frontend/      # React + TypeScript SPA
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with:

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

Run migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Seed demo data (3 stores, 29 employees, 3 weeks of published shifts):

```bash
python -m scripts.seed_data_v5
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

The Vite dev server proxies `/api/*` to the backend at `http://localhost:8000`.

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@shiftpilot.work | admin123 |
| Manager (London) | sarah.johnson@shiftpilot.work | manager123 |
| Manager (Manchester) | david.roberts@shiftpilot.work | manager123 |
| Manager (Bristol) | alex.reed@shiftpilot.work | manager123 |
| Employee | `<firstname>.<surname>@shiftpilot.work` | employee123 |

## Running Tests

```bash
cd backend
pytest
```
