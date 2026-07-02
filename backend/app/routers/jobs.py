from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Queue, Project, ScheduledJob, User
from app.schemas import JobCreate, JobOut, PaginatedJobs
from app.security import get_current_user

router = APIRouter(prefix="/projects/{project_id}/queues/{queue_id}/jobs", tags=["jobs"])


def _get_owned_queue(db: Session, project_id: str, queue_id: str, user: User) -> Queue:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.org_id == user.org_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    queue = db.query(Queue).filter(Queue.id == queue_id, Queue.project_id == project_id).first()
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    return queue


def _compute_run_at(payload: JobCreate) -> datetime:
    """Resolves the earliest-eligible-claim time based on job_type."""
    now = datetime.utcnow()

    if payload.job_type == "immediate":
        return now

    if payload.job_type == "delayed":
        if payload.delay_seconds is None:
            raise HTTPException(status_code=400, detail="delay_seconds is required for delayed jobs")
        return now + timedelta(seconds=payload.delay_seconds)

    if payload.job_type == "scheduled":
        if payload.run_at is None:
            raise HTTPException(status_code=400, detail="run_at is required for scheduled jobs")
        if payload.run_at <= now:
            raise HTTPException(status_code=400, detail="run_at must be in the future")
        return payload.run_at

    if payload.job_type == "recurring":
        if not payload.cron_expression:
            raise HTTPException(status_code=400, detail="cron_expression is required for recurring jobs")
        # First run_at is "now" — APScheduler (Milestone 8) takes over
        # scheduling subsequent occurrences via ScheduledJob.next_run_at.
        return now

    if payload.job_type == "batch":
        if not payload.batch_size:
            raise HTTPException(status_code=400, detail="batch_size is required for batch jobs")
        return now

    raise HTTPException(status_code=400, detail="Unsupported job_type")


@router.post("", response_model=list[JobOut], status_code=201)
def create_job(
    project_id: str,
    queue_id: str,
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    queue = _get_owned_queue(db, project_id, queue_id, user)

    if queue.is_paused:
        raise HTTPException(status_code=400, detail="Queue is paused; cannot accept new jobs")

    run_at = _compute_run_at(payload)

    # Batch jobs: create N independent job rows sharing one payload/priority.
    # Each is claimed and executed independently by workers — this is
    # simpler and more fault-tolerant than one "batch" row workers would
    # need to split internally.
    count = payload.batch_size if payload.job_type == "batch" else 1

    created_jobs = []
    for _ in range(count):
        job = Job(
            queue_id=queue_id,
            job_type=payload.job_type,
            payload=payload.payload,
            priority=payload.priority,
            run_at=run_at,
        )
        db.add(job)
        db.flush()

        if payload.job_type == "recurring":
            db.add(ScheduledJob(job_id=job.id, cron_expression=payload.cron_expression))

        created_jobs.append(job)

    db.commit()
    for job in created_jobs:
        db.refresh(job)
    return created_jobs


@router.get("", response_model=PaginatedJobs)
def list_jobs(
    project_id: str,
    queue_id: str,
    status: Optional[str] = Query(default=None, pattern="^(pending|running|completed|failed|dead_letter)$"),
    job_type: Optional[str] = Query(default=None, pattern="^(immediate|delayed|scheduled|recurring|batch)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_queue(db, project_id, queue_id, user)

    query = db.query(Job).filter(Job.queue_id == queue_id)
    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.job_type == job_type)

    total = query.count()
    items = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedJobs(items=items, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    project_id: str,
    queue_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_queue(db, project_id, queue_id, user)

    job = db.query(Job).filter(Job.id == job_id, Job.queue_id == queue_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
def cancel_job(
    project_id: str,
    queue_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_queue(db, project_id, queue_id, user)

    job = db.query(Job).filter(Job.id == job_id, Job.queue_id == queue_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "running":
        raise HTTPException(status_code=400, detail="Cannot cancel a job that is currently running")

    db.delete(job)
    db.commit()
    return None