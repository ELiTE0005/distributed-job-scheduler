from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Queue, Project, RetryPolicy, User
from app.schemas import QueueCreate, QueueUpdate, QueueOut, PaginatedQueues
from app.security import get_current_user

router = APIRouter(prefix="/projects/{project_id}/queues", tags=["queues"])


def _get_owned_project(db: Session, project_id: str, user: User) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.org_id == user.org_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=QueueOut, status_code=201)
def create_queue(
    project_id: str,
    payload: QueueCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)

    existing = (
        db.query(Queue)
        .filter(Queue.project_id == project_id, Queue.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Queue name already exists in this project")

    queue = Queue(project_id=project_id, name=payload.name, max_concurrency=payload.max_concurrency)
    db.add(queue)
    db.flush()

    # Every queue gets a default retry policy — required by RetryPolicy's
    # unique constraint on queue_id and by the worker's retry logic (Milestone 7).
    db.add(RetryPolicy(queue_id=queue.id, strategy="exponential", max_attempts=3, base_delay_seconds=10))

    db.commit()
    db.refresh(queue)
    return queue


@router.get("", response_model=PaginatedQueues)
def list_queues(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)

    query = db.query(Queue).filter(Queue.project_id == project_id)
    total = query.count()
    items = (
        query.order_by(Queue.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedQueues(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{queue_id}", response_model=QueueOut)
def update_queue(
    project_id: str,
    queue_id: str,
    payload: QueueUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)

    queue = db.query(Queue).filter(Queue.id == queue_id, Queue.project_id == project_id).first()
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    if payload.max_concurrency is not None:
        queue.max_concurrency = payload.max_concurrency
    if payload.is_paused is not None:
        queue.is_paused = payload.is_paused  # powers "Pause/Resume" queue feature

    db.commit()
    db.refresh(queue)
    return queue


@router.delete("/{queue_id}", status_code=204)
def delete_queue(
    project_id: str,
    queue_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)

    queue = db.query(Queue).filter(Queue.id == queue_id, Queue.project_id == project_id).first()
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    db.delete(queue)
    db.commit()
    return None