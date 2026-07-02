# Distributed Job Scheduler

A production-inspired distributed job scheduler demonstrating polling-based
distributed systems concepts (atomic claiming, worker heartbeats, retry
strategies) without external brokers like Redis/Celery/RabbitMQ.

## Status
🚧 In active development — see `docs/architecture.md` for design.

## Stack
- Backend: FastAPI, SQLAlchemy, PostgreSQL, JWT, APScheduler
- Frontend: React, Vite, Tailwind CSS, Recharts