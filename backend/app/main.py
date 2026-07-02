from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth

# Creates all tables from models.py if they don't exist yet.
# Acceptable for this project's scope in place of Alembic migrations
# (see docs/schema.md "Why no Alembic?").
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Distributed Job Scheduler API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

from app.routers import auth, projects, queues

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(queues.router)

from app.routers import auth, projects, queues, jobs

app.include_router(jobs.router)