import time
import socket
import random
import logging
import signal
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Worker, WorkerHeartbeat, Job, JobExecution, JobLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

POLL_INTERVAL_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 5

# THE ATOMIC CLAIM.
# FOR UPDATE SKIP LOCKED is what makes N concurrent workers safe against
# the same table with zero coordination: each worker's transaction takes
# a row lock on the candidate job. Any *other* worker's simultaneous
# SELECT simply skips rows that are already locked instead of blocking or
# double-claiming them. Combined with WHERE status='pending', two workers
# can never walk away with the same job — Postgres guarantees it at the
# row-lock level, not in application code.
CLAIM_JOB_SQL = text("""
    UPDATE jobs
    SET status = 'running',
        claimed_by = :worker_id,
        attempt_count = attempt_count + 1,
        updated_at = now()
    WHERE id = (
        SELECT id FROM jobs
        WHERE status = 'pending' AND run_at <= now()
        ORDER BY priority DESC, run_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING id, queue_id, job_type, payload, attempt_count
""")


class WorkerService:
    def __init__(self, hostname: str = None, concurrency: int = 3):
        self.hostname = hostname or socket.gethostname()
        self.concurrency = concurrency
        self.worker_id = None
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=concurrency)
        self._active_futures = []

    # ---------- Lifecycle ----------

    def start(self):
        self._register()
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

        logger.info(f"Worker {self.worker_id} started on {self.hostname} (concurrency={self.concurrency})")
        self._poll_loop()

    def _register(self):
        db = SessionLocal()
        try:
            worker = Worker(hostname=self.hostname, status="idle")
            db.add(worker)
            db.commit()
            db.refresh(worker)
            self.worker_id = worker.id
        finally:
            db.close()

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received. Finishing in-flight jobs, then exiting...")
        self._stop_event.set()

    # ---------- Heartbeat ----------

    def _heartbeat_loop(self):
        while not self._stop_event.is_set():
            db = SessionLocal()
            try:
                db.add(WorkerHeartbeat(worker_id=self.worker_id))
                db.query(Worker).filter(Worker.id == self.worker_id).update(
                    {"last_seen_at": datetime.utcnow()}
                )
                db.commit()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                db.rollback()
            finally:
                db.close()
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    # ---------- Poll & claim ----------

    def _poll_loop(self):
        while not self._stop_event.is_set():
            self._active_futures = [f for f in self._active_futures if not f.done()]
            free_slots = self.concurrency - len(self._active_futures)

            if free_slots <= 0:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            claimed = self._claim_job()
            if claimed is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            future = self._executor.submit(self._execute_job, claimed)
            self._active_futures.append(future)

        logger.info("Waiting for in-flight jobs to finish...")
        self._executor.shutdown(wait=True)
        self._set_worker_status("offline")
        logger.info("Worker shut down cleanly.")

    def _claim_job(self):
        db = SessionLocal()
        try:
            result = db.execute(CLAIM_JOB_SQL, {"worker_id": self.worker_id})
            row = result.fetchone()
            db.commit()
            return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"Claim failed: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    # ---------- Execution ----------

    def _execute_job(self, job: dict):
        job_id = job["id"]
        self._set_worker_status("busy")

        db = SessionLocal()
        execution = JobExecution(job_id=job_id, worker_id=self.worker_id, status="running")
        db.add(execution)
        db.commit()
        db.refresh(execution)

        self._log(db, execution.id, "INFO",
                   f"Started job {job_id} (type={job['job_type']}, attempt={job['attempt_count']})")

        try:
            # Simulated task execution — a real task registry keyed on
            # payload['task'] would dispatch here. Kept simulated to stay
            # in scope for the assignment's timeframe.
            time.sleep(random.uniform(0.5, 2.0))
            if random.random() < 0.8:
                self._mark_success(db, execution, job_id)
                self._log(db, execution.id, "INFO", f"Job {job_id} completed successfully")
            else:
                raise RuntimeError("Simulated task failure")
        except Exception as e:
            self._mark_failure(db, execution, job_id, reason=str(e))
            self._log(db, execution.id, "ERROR", f"Job {job_id} failed: {e}")
        finally:
            db.close()
            self._set_worker_status("idle")

    def _mark_success(self, db: Session, execution: JobExecution, job_id: str):
        execution.status = "completed"
        execution.finished_at = datetime.utcnow()
        db.query(Job).filter(Job.id == job_id).update({"status": "completed", "updated_at": datetime.utcnow()})
        db.commit()

    def _mark_failure(self, db: Session, execution: JobExecution, job_id: str, reason: str):
        execution.status = "failed"
        execution.finished_at = datetime.utcnow()
        db.commit()

        from app.retry_logic import handle_job_failure
        handle_job_failure(db, job_id, failure_reason=reason)

    def _set_worker_status(self, status: str):
        db = SessionLocal()
        try:
            db.query(Worker).filter(Worker.id == self.worker_id).update({"status": status})
            db.commit()
        finally:
            db.close()

    def _log(self, db: Session, execution_id: str, level: str, message: str):
        db.add(JobLog(execution_id=execution_id, level=level, message=message))
        db.commit()
        logger.info(message)