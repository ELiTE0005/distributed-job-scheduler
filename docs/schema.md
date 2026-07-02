---
noteId: "5921b0d075fa11f19da9b92d8ec5cc78"
tags: []

---

# Database Design Notes

## Normalization
Schema is in 3NF. No repeating groups; every non-key column depends only on
its table's primary key (e.g. `retry_policies` is split out from `queues`
rather than adding nullable retry columns to every queue row).

## Key Design Decisions

**Why a composite index on `jobs(status, run_at, priority)`?**
This is the exact predicate + order the worker's polling query uses
(`WHERE status='pending' AND run_at <= now() ORDER BY priority DESC`).
Without it, every poll is a full table scan once the jobs table grows.

**Why `claimed_by` on the job row instead of a separate claims table?**
Keeps the atomic claim to a single `UPDATE ... WHERE status='pending'`
statement (Milestone 6) — one row, one lock, no join needed to check
ownership.

**Cascade rules:**
- `Organization → Users/Projects`: `ON DELETE CASCADE` — deleting a tenant
  removes its data entirely (expected for a demo/multi-tenant model).
- `Queue → Jobs/RetryPolicy`: `CASCADE` — a queue's lifecycle owns its jobs.
- `Job → JobExecutions/ScheduledJob/DeadLetterQueue`: `CASCADE` — these are
  pure children of a job's identity.
- `Worker → JobExecution.worker_id` and `Job.claimed_by`: `SET NULL` — a
  worker being decommissioned shouldn't destroy historical execution
  records or orphan a job's audit trail.

**Why no Alembic?** No schema migrations happen after initial design in
this project's timeframe. `Base.metadata.create_all()` is used once at
startup. Tradeoff documented here rather than adding migration tooling
that wouldn't be exercised — noted explicitly in the final README's
"Design Decisions" section.

## Tables
Organizations, Users, Projects, Queues, RetryPolicies, Jobs, ScheduledJobs,
Workers, WorkerHeartbeats, JobExecutions, JobLogs, DeadLetterQueue — 12
tables matching the ER diagram in `architecture.md`.