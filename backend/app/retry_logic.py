from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Job, Queue, RetryPolicy, DeadLetterQueue


def compute_backoff_seconds(strategy: str, base_delay: int, attempt_count: int) -> int:
    """
    Pure function — no DB access — so it's trivially unit-testable (Milestone 13).

    fixed:        always base_delay
    linear:       base_delay * attempt_count
    exponential:  base_delay * 2^(attempt_count - 1)
    """
    if strategy == "fixed":
        return base_delay
    if strategy == "linear":
        return base_delay * attempt_count
    if strategy == "exponential":
        return base_delay * (2 ** (attempt_count - 1))
    raise ValueError(f"Unknown retry strategy: {strategy}")


def handle_job_failure(db: Session, job_id: str, failure_reason: str):
    """
    Called after a job execution fails. Either reschedules the job with a
    backoff delay, or routes it to the Dead Letter Queue if attempts are
    exhausted. This is the single place retry policy is enforced, so
    Milestone 6's worker and any future admin "force retry" endpoint both
    go through the same logic.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return

    queue = db.query(Queue).filter(Queue.id == job.queue_id).first()
    policy = db.query(RetryPolicy).filter(RetryPolicy.queue_id == queue.id).first()

    if job.attempt_count >= policy.max_attempts:
        job.status = "dead_letter"
        db.add(DeadLetterQueue(job_id=job.id, failure_reason=failure_reason))
    else:
        delay = compute_backoff_seconds(policy.strategy, policy.base_delay_seconds, job.attempt_count)
        job.status = "pending"
        job.run_at = datetime.utcnow() + timedelta(seconds=delay)

    job.updated_at = datetime.utcnow()
    db.commit()