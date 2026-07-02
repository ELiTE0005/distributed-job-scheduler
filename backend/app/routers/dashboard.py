from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Job, Queue, Project, Worker, DeadLetterQueue, User
from app.schemas import DashboardStats, JobStatusCounts, QueueSummary, WorkerSummary
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Scope everything to the current org via a Project join — this is the
    # same multi-tenancy boundary used throughout the app (Milestone 4).
    org_project_ids = [p.id for p in db.query(Project.id).filter(Project.org_id == user.org_id)]
    org_queue_ids = [q.id for q in db.query(Queue.id).filter(Queue.project_id.in_(org_project_ids))]

    # ---- Job status counts (single grouped query, not 5 separate counts) ----
    status_rows = (
        db.query(Job.status, func.count(Job.id))
        .filter(Job.queue_id.in_(org_queue_ids))
        .group_by(Job.status)
        .all()
    )
    counts = JobStatusCounts()
    for status, count in status_rows:
        setattr(counts, status, count)
    total_jobs = sum(dict(status_rows).values()) if status_rows else 0

    # ---- Per-queue summary ----
    queues = db.query(Queue).filter(Queue.project_id.in_(org_project_ids)).all()
    queue_summaries = []
    for q in queues:
        pending = db.query(func.count(Job.id)).filter(Job.queue_id == q.id, Job.status == "pending").scalar()
        running = db.query(func.count(Job.id)).filter(Job.queue_id == q.id, Job.status == "running").scalar()
        queue_summaries.append(QueueSummary(
            id=q.id, name=q.name, is_paused=q.is_paused,
            max_concurrency=q.max_concurrency, pending_jobs=pending, running_jobs=running,
        ))

    # ---- Workers (global, not org-scoped — workers aren't tenant-owned
    # in this simplified model; noted as a tradeoff in docs) ----
    workers = db.query(Worker).order_by(Worker.last_seen_at.desc()).limit(20).all()
    worker_summaries = [
        WorkerSummary(id=w.id, hostname=w.hostname, status=w.status, last_seen_at=w.last_seen_at)
        for w in workers
    ]

    dead_letter_count = (
        db.query(func.count(DeadLetterQueue.id))
        .join(Job, Job.id == DeadLetterQueue.job_id)
        .filter(Job.queue_id.in_(org_queue_ids))
        .scalar()
    )

    return DashboardStats(
        job_status_counts=counts,
        total_jobs=total_jobs,
        queues=queue_summaries,
        workers=worker_summaries,
        dead_letter_count=dead_letter_count,
    )