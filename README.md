Distributed Job Orchestration Platform (FastAPI)
Overview

This project is a production-grade Distributed Job Scheduler and Orchestration Platform built using FastAPI.
It is designed to reflect real-world industry systems used for background processing, workflow orchestration, and fault-tolerant job execution at scale.

The system supports DAG-based workflows, distributed workers, retries with backoff, idempotency, and full observability, inspired by platforms like Temporal, Apache Airflow, AWS Step Functions, and Celery.

⚠️ This is not a cron replacement.
It is a control-plane + execution-plane distributed system.

Core Goals

Handle highly concurrent job submissions

Support complex workflows (DAGs)

Ensure fault tolerance and recovery

Guarantee idempotent execution

Be observable, debuggable, and scalable

Remain cloud-agnostic

System Architecture
Clients (API / Webhooks / UI)
        |
        v
FastAPI API Gateway (Control Plane)
- Auth & RBAC
- Job submission
- Workflow definition
- Admin APIs
        |
        v
Job Orchestrator
- DAG resolution
- Dependency tracking
- State machine
- Scheduling logic
        |
        v
Message Broker (Redis / RabbitMQ / Kafka)
        |
        v
Distributed Worker Pool (Execution Plane)
- Parallel job execution
- Heartbeats
- Idempotency
- Retries
        |
        v
Persistence Layer
- PostgreSQL (jobs, workflows, state)
- Redis (locks, queues, cache)
        |
        v
Observability Stack
- Logs
- Metrics
- Traces

Key Concepts
1. Job as a State Machine

Each job is modeled as a persistent state machine, not a function call.

Job States
PENDING → SCHEDULED → RUNNING
        → SUCCESS
        → FAILED → RETRYING → DEAD
        → CANCELED

Job Attributes
Field	Description
job_id	Unique job identifier
type	Job type (email, webhook, ETL, etc.)
payload	JSON payload
priority	Execution priority
max_retries	Retry limit
retry_policy	fixed / exponential / jitter
timeout	Execution timeout
idempotency_key	Prevents duplicate execution
parent_job_id	For DAG workflows
status	Current job state
scheduled_at	Scheduled execution time
2. Workflow / DAG Support

Jobs can be composed into Directed Acyclic Graphs (DAGs).

Example Workflow
Order Processing Workflow
│
├── Validate Order
├── Reserve Inventory
├── Charge Payment
│   ├── Fraud Check
│   └── Payment Gateway
├── Generate Invoice
└── Send Notifications

DAG Rules

Jobs execute only after dependencies succeed

Partial retries are supported

DAG execution state is persisted

Failure propagation is explicit

3. Scheduling Strategies

The scheduler supports multiple scheduling types:

Immediate execution

Delayed execution

Cron-based recurring jobs

Event-driven jobs (webhooks)

Retry-based rescheduling with backoff

FastAPI Responsibilities (Control Plane)

FastAPI does not execute jobs.
It coordinates and orchestrates.

Responsibilities

Job submission & validation

Workflow/DAG definitions

Scheduling metadata

Admin controls (pause, resume, cancel)

Webhook ingestion

Observability endpoints

Example Endpoints
POST   /jobs
POST   /workflows
GET    /jobs/{job_id}
GET    /workflows/{workflow_id}/status
POST   /jobs/{job_id}/cancel
POST   /workers/heartbeat

Distributed Workers (Execution Plane)

Workers are stateless and horizontally scalable.

Worker Responsibilities

Pull jobs from broker

Acquire distributed lock

Execute job

Emit heartbeat

Report completion or failure

Failure Handling
Scenario	Handling
Worker crash	Job reassigned
Timeout	Job marked failed
Duplicate execution	Prevented via idempotency

Execution guarantee:

At-least-once delivery with idempotent execution

Concurrency & Safety Guarantees
API-Level Concurrency

FastAPI async handling (ASGI)

No blocking operations

High-throughput job ingestion

Scheduler-Level Concurrency

Atomic job claiming

DB row locking (SELECT … FOR UPDATE SKIP LOCKED)

No duplicate scheduling

Worker-Level Concurrency

Parallel execution

Configurable concurrency limits

Backpressure support

Data-Level Concurrency

Atomic state transitions

Optimistic checks on job state

Distributed locks for side effects

Idempotency

Every job requires an idempotency_key

DB-level uniqueness constraints

Cached execution results

Safe retries under concurrency

This ensures:

Client retries are safe

Network retries are safe

Worker crashes do not cause duplication

Observability (Mandatory)
Metrics

Job success/failure rates

Retry counts

Queue latency

Worker utilization

Scheduler lag

Logs

Structured JSON logs

Correlation IDs per job/workflow

Traces

Parent job → child job trace linkage

End-to-end workflow tracing

Security & Governance

JWT / API key authentication

Role-based access control (admin, user)

Tenant-level job quotas

Rate limiting per client

Deployment & Scalability

Fully Dockerized

Horizontal scaling for workers

Broker-based decoupling

Database migrations supported

Environment-based configuration

The system is cloud-agnostic and can run on any VPS, Kubernetes, or managed cloud environment.

Tech Stack

FastAPI – API & orchestration layer

PostgreSQL – Persistent state & workflows

Redis – Locks, queues, caching

Message Broker – Redis / RabbitMQ / Kafka

Docker – Containerization

Prometheus / OpenTelemetry – Observability

Design Trade-offs (Documented)

Redis vs Kafka for broker

DB locking vs distributed locks

At-least-once vs exactly-once execution

Polling vs event-driven scheduling

Comparable Industry Systems (Conceptual)

This project is conceptually inspired by:

Temporal

Apache Airflow

AWS Step Functions

Celery

This is a simplified but production-oriented implementation, not a clone.

What Makes This Senior-Level

✅ Distributed architecture
✅ DAG orchestration
✅ Concurrency-safe scheduling
✅ Failure recovery
✅ Idempotency
✅ Observability-first design
✅ Clear separation of control & execution planes

Execution Roadmap (AI Agent Friendly)
Phase 1 – Foundations

DB schema (jobs, workflows, state)

Job state machine

API skeleton

Phase 2 – Scheduling & DAGs

Dependency resolution

Atomic job claiming

Retry policies

Phase 3 – Workers

Broker integration

Parallel execution

Heartbeats

Phase 4 – Reliability

Idempotency

Failure recovery

Locking

Phase 5 – Observability & Hardening

Metrics

Logs

Load testing

Final Note

If ~70% of this system is implemented correctly, it can be confidently presented as senior-level backend engineering work.

This repository prioritizes correctness, scalability, and real-world design over shortcuts or demo-only patterns.