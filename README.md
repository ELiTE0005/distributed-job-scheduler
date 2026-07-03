# Distributed Job Scheduler

A production-inspired distributed job scheduler built with FastAPI, PostgreSQL,
and React — demonstrating core distributed-systems concepts (atomic job
claiming, worker heartbeats, retry strategies, dead letter queues) using
Postgres row-locking instead of external brokers like Redis/Celery/RabbitMQ.

## Architecture
See `docs/architecture.md` for full system, ER, sequence, worker-flow, and
retry-flow diagrams. See `docs/schema.md` for database design rationale.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, JWT auth, APScheduler
- **Frontend**: React, Vite, Tailwind CSS, Recharts
- **Worker**: Python threading + `FOR UPDATE SKIP LOCKED` atomic claiming

## Key Design Decisions
- **No message broker**: Jobs live in a single `jobs` table. Workers poll
  and atomically claim rows via `SELECT ... FOR UPDATE SKIP LOCKED`,
  guaranteeing no job is ever double-processed across concurrent workers —
  without Redis/Celery/RabbitMQ.
- **5 job types** (immediate, delayed, scheduled, recurring, batch) all
  resolve to a single `run_at` timestamp at creation time, so the worker's
  claim logic stays identical regardless of job type.
- **Retry strategies** (fixed/linear/exponential backoff) and dead-letter
  routing are enforced in one pure function (`retry_logic.py`), reused by
  the worker and testable without a database.
- **No Alembic**: schema is created via `Base.metadata.create_all()` since
  no migrations were needed in this project's scope — documented tradeoff.

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
cp .env.example .env
psql -h localhost -U postgres -c "CREATE DATABASE job_scheduler;"
uvicorn app.main:app --reload --port 8000
```
API docs: `http://127.0.0.1:8000/docs`

### Worker
```bash
cd backend
python run_worker.py --concurrency 3
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App: `http://localhost:5173`

## Tradeoffs & Future Improvements
- No dead-worker detection via missed heartbeats.
- Job execution is simulated (random success/failure) rather than
  dispatching to a real task registry — kept in scope for the assignment's
  timeframe.
- Workers are not multi-tenant scoped in this simplified model.
- Automated tests (auth, retry logic, worker claim) were planned but
  deprioritized under time constraints in favor of full documentation.