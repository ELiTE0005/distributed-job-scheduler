import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, DateTime,
    Text, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------- Organizations & Users ----------

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="member")  # admin | member
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="users")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member')", name="ck_user_role"),
    )


# ---------- Projects & Queues ----------

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="projects")
    queues = relationship("Queue", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_projects_org_id", "org_id"),
    )


class Queue(Base):
    __tablename__ = "queues"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    max_concurrency = Column(Integer, nullable=False, default=5)
    is_paused = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="queues")
    jobs = relationship("Job", back_populates="queue", cascade="all, delete-orphan")
    retry_policy = relationship("RetryPolicy", back_populates="queue", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_queue_name_per_project"),
        Index("ix_queues_project_id", "project_id"),
    )


class RetryPolicy(Base):
    __tablename__ = "retry_policies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    queue_id = Column(UUID(as_uuid=False), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, unique=True)
    strategy = Column(String(20), nullable=False, default="exponential")  # fixed | linear | exponential
    max_attempts = Column(Integer, nullable=False, default=3)
    base_delay_seconds = Column(Integer, nullable=False, default=10)

    queue = relationship("Queue", back_populates="retry_policy")

    __table_args__ = (
        CheckConstraint("strategy IN ('fixed', 'linear', 'exponential')", name="ck_retry_strategy"),
    )


# ---------- Jobs ----------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    queue_id = Column(UUID(as_uuid=False), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(20), nullable=False)  # immediate | delayed | scheduled | recurring | batch
    status = Column(String(20), nullable=False, default="pending", index=True)
    # pending | running | completed | failed | dead_letter
    priority = Column(Integer, nullable=False, default=0)  # higher = more urgent
    payload = Column(JSONB, nullable=False, default=dict)
    attempt_count = Column(Integer, nullable=False, default=0)
    run_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # earliest eligible claim time
    claimed_by = Column(UUID(as_uuid=False), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    queue = relationship("Queue", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")
    scheduled_job = relationship("ScheduledJob", back_populates="job", uselist=False, cascade="all, delete-orphan")
    dead_letter_entry = relationship("DeadLetterQueue", back_populates="job", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('immediate','delayed','scheduled','recurring','batch')",
            name="ck_job_type",
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','failed','dead_letter')",
            name="ck_job_status",
        ),
        # Composite index is THE critical index — it's exactly what the
        # worker's polling/claim query filters and orders by.
        Index("ix_jobs_claim_lookup", "status", "run_at", "priority"),
    )


class ScheduledJob(Base):
    """Recurring job definition, driven by APScheduler (Milestone 8)."""
    __tablename__ = "scheduled_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    cron_expression = Column(String(100), nullable=False)
    next_run_at = Column(DateTime, nullable=True)

    job = relationship("Job", back_populates="scheduled_job")


# ---------- Workers ----------

class Worker(Base):
    __tablename__ = "workers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hostname = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="idle")  # idle | busy | offline
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    heartbeats = relationship("WorkerHeartbeat", back_populates="worker", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('idle','busy','offline')", name="ck_worker_status"),
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    worker_id = Column(UUID(as_uuid=False), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    worker = relationship("Worker", back_populates="heartbeats")

    __table_args__ = (
        Index("ix_heartbeats_worker_sent", "worker_id", "sent_at"),
    )


# ---------- Execution & Logs ----------

class JobExecution(Base):
    __tablename__ = "job_executions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    worker_id = Column(UUID(as_uuid=False), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False)  # running | completed | failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    job = relationship("Job", back_populates="executions")
    logs = relationship("JobLog", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_executions_job_id", "job_id"),
        Index("ix_executions_worker_id", "worker_id"),
    )


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    execution_id = Column(UUID(as_uuid=False), ForeignKey("job_executions.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), nullable=False, default="INFO")  # INFO | WARN | ERROR
    message = Column(Text, nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("JobExecution", back_populates="logs")

    __table_args__ = (
        Index("ix_logs_execution_id", "execution_id"),
    )


class DeadLetterQueue(Base):
    __tablename__ = "dead_letter_queue"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    failure_reason = Column(Text, nullable=False)
    moved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="dead_letter_entry")