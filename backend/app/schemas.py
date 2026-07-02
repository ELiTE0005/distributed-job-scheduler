from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class UserRegister(BaseModel):
    org_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    org_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Projects ----------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProjectOut(BaseModel):
    id: str
    org_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedProjects(BaseModel):
    items: List[ProjectOut]
    total: int
    page: int
    page_size: int


# ---------- Queues ----------

class QueueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    max_concurrency: int = Field(default=5, ge=1, le=100)


class QueueUpdate(BaseModel):
    max_concurrency: Optional[int] = Field(default=None, ge=1, le=100)
    is_paused: Optional[bool] = None


class QueueOut(BaseModel):
    id: str
    project_id: str
    name: str
    max_concurrency: int
    is_paused: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedQueues(BaseModel):
    items: List[QueueOut]
    total: int
    page: int
    page_size: int






# ---------- Jobs ----------

class JobCreate(BaseModel):
    job_type: str = Field(..., pattern="^(immediate|delayed|scheduled|recurring|batch)$")
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)

    # delayed: run once, after `delay_seconds`
    delay_seconds: Optional[int] = Field(default=None, ge=0)

    # scheduled: run once, at a specific timestamp
    run_at: Optional[datetime] = None

    # recurring: run repeatedly per cron expression (APScheduler, Milestone 8)
    cron_expression: Optional[str] = None

    # batch: N copies of the same payload submitted as one call
    batch_size: Optional[int] = Field(default=None, ge=1, le=100)


class JobOut(BaseModel):
    id: str
    queue_id: str
    job_type: str
    status: str
    priority: int
    payload: dict
    attempt_count: int
    run_at: datetime
    claimed_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedJobs(BaseModel):
    items: List[JobOut]
    total: int
    page: int
    page_size: int