import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models import Job, ScheduledJob

logger = logging.getLogger("scheduler")

CHECK_INTERVAL_SECONDS = 30


def _spawn_next_occurrence(scheduled_job_id: str):
    """
    Runs on APScheduler's own thread. For a given recurring job definition,
    inserts a fresh pending Job row — the actual execution is still handled
    by the normal worker poll/claim loop (Milestone 6), so recurring jobs
    get identical retry/DLQ/concurrency behavior to every other job type
    for free.
    """
    db = SessionLocal()
    try:
        scheduled = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
        if not scheduled:
            return  # definition was deleted; nothing to do

        original_job = db.query(Job).filter(Job.id == scheduled.job_id).first()
        if not original_job:
            return

        new_job = Job(
            queue_id=original_job.queue_id,
            job_type="recurring",
            payload=original_job.payload,
            priority=original_job.priority,
            run_at=datetime.utcnow(),
        )
        db.add(new_job)
        db.commit()
        logger.info(f"Spawned recurring occurrence {new_job.id} from schedule {scheduled_job_id}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """
    Called once when the worker process starts. Loads every existing
    ScheduledJob row and registers a cron trigger for each, then polls
    every CHECK_INTERVAL_SECONDS for newly created recurring jobs (created
    via the API after the worker already started) and registers those too.
    """
    scheduler = BackgroundScheduler()
    registered_ids = set()

    def _sync_jobs():
        db = SessionLocal()
        try:
            scheduled_jobs = db.query(ScheduledJob).all()
            for sj in scheduled_jobs:
                if sj.id in registered_ids:
                    continue
                try:
                    trigger = CronTrigger.from_crontab(sj.cron_expression)
                    scheduler.add_job(
                        _spawn_next_occurrence,
                        trigger=trigger,
                        args=[sj.id],
                        id=f"recurring-{sj.id}",
                        replace_existing=True,
                    )
                    registered_ids.add(sj.id)
                    logger.info(f"Registered recurring schedule {sj.id} ({sj.cron_expression})")
                except Exception as e:
                    logger.error(f"Invalid cron expression for {sj.id}: {e}")
        finally:
            db.close()

    _sync_jobs()  # register anything that already exists at startup
    scheduler.add_job(_sync_jobs, "interval", seconds=CHECK_INTERVAL_SECONDS)
    scheduler.start()
    logger.info("APScheduler started")
    return scheduler