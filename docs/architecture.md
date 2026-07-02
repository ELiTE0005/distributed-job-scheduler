---
noteId: "58c1abf075f911f19da9b92d8ec5cc78"
tags: []

---

# Architecture

## 1. System Architecture

​```mermaid
flowchart LR
    subgraph Client
        UI[React Dashboard]
    end

    subgraph API Layer
        API[FastAPI App]
    end

    subgraph Data Layer
        DB[(PostgreSQL)]
    end

    subgraph Execution Layer
        W1[Worker Process 1]
        W2[Worker Process 2]
        SCHED[APScheduler
Recurring Job Trigger]
    end

    UI -- REST + Polling --> API
    API -- CRUD --> DB
    W1 -- Poll & Claim --> DB
    W2 -- Poll & Claim --> DB
    SCHED -- Insert Due Jobs --> DB
​```

**Why no message broker?** Jobs live in a single `jobs` table acting as the
queue. Workers poll it with a `SELECT ... FOR UPDATE SKIP LOCKED`-style
atomic claim (Milestone 6). This gives real distributed-systems guarantees
(no double-processing, safe concurrency) without Redis/Celery/RabbitMQ.

## 2. Entity-Relationship Diagram

​```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ QUEUES : contains
    QUEUES ||--o{ JOBS : holds
    QUEUES ||--o{ RETRY_POLICIES : configured_by
    JOBS ||--o{ JOB_EXECUTIONS : produces
    JOBS ||--o| SCHEDULED_JOBS : may_have
    JOB_EXECUTIONS ||--o{ JOB_LOGS : generates
    JOB_EXECUTIONS }o--|| WORKERS : executed_by
    WORKERS ||--o{ WORKER_HEARTBEATS : sends
    JOBS ||--o| DEAD_LETTER_QUEUE : ends_in

    ORGANIZATIONS {
        uuid id PK
        string name
        timestamp created_at
    }
    USERS {
        uuid id PK
        uuid org_id FK
        string email
        string hashed_password
        string role
    }
    PROJECTS {
        uuid id PK
        uuid org_id FK
        string name
        timestamp created_at
    }
    QUEUES {
        uuid id PK
        uuid project_id FK
        string name
        int max_concurrency
        boolean is_paused
    }
    JOBS {
        uuid id PK
        uuid queue_id FK
        string job_type
        string status
        int priority
        jsonb payload
        int attempt_count
        timestamp run_at
        timestamp created_at
    }
    RETRY_POLICIES {
        uuid id PK
        uuid queue_id FK
        string strategy
        int max_attempts
        int base_delay_seconds
    }
    WORKERS {
        uuid id PK
        string hostname
        string status
        timestamp last_seen_at
    }
    WORKER_HEARTBEATS {
        uuid id PK
        uuid worker_id FK
        timestamp sent_at
    }
    JOB_EXECUTIONS {
        uuid id PK
        uuid job_id FK
        uuid worker_id FK
        string status
        timestamp started_at
        timestamp finished_at
    }
    JOB_LOGS {
        uuid id PK
        uuid execution_id FK
        string level
        text message
        timestamp logged_at
    }
    SCHEDULED_JOBS {
        uuid id PK
        uuid job_id FK
        string cron_expression
        timestamp next_run_at
    }
    DEAD_LETTER_QUEUE {
        uuid id PK
        uuid job_id FK
        text failure_reason
        timestamp moved_at
    }
​```

## 3. Job Lifecycle Sequence

​```mermaid
sequenceDiagram
    participant U as User (API)
    participant DB as PostgreSQL
    participant W as Worker

    U->>DB: INSERT job (status=pending)
    loop Poll interval
        W->>DB: SELECT pending jobs FOR UPDATE SKIP LOCKED
        DB-->>W: 1 job row
        W->>DB: UPDATE status=running, worker_id=W
    end
    W->>W: Execute job payload
    alt Success
        W->>DB: UPDATE status=completed
    else Failure
        W->>DB: Check retry_policy
        alt attempts < max_attempts
            W->>DB: UPDATE status=pending, run_at=now+backoff
        else
            W->>DB: INSERT INTO dead_letter_queue
        end
    end
​```

## 4. Worker Flow

​```mermaid
flowchart TD
    A[Start Worker] --> B[Send Heartbeat]
    B --> C{Poll for claimable job}
    C -- None found --> D[Sleep poll_interval] --> B
    C -- Job found --> E[Atomically claim: UPDATE ... WHERE status=pending]
    E --> F[Execute job]
    F --> G{Success?}
    G -- Yes --> H[Mark completed] --> B
    G -- No --> I[Apply Retry Policy] --> B
    B --> J{Shutdown signal?}
    J -- Yes --> K[Finish current job, exit cleanly]
​```

## 5. Retry Flow

​```mermaid
flowchart TD
    A[Job Failed] --> B{attempt_count < max_attempts?}
    B -- No --> C[Move to Dead Letter Queue]
    B -- Yes --> D{Strategy}
    D -- Fixed --> E[delay = base_delay]
    D -- Linear --> F[delay = base_delay * attempt_count]
    D -- Exponential --> G[delay = base_delay * 2^attempt_count]
    E --> H[run_at = now + delay, status=pending]
    F --> H
    G --> H
​```