"""Prometheus metrics for Schedora."""
from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Optional
from sqlalchemy.orm import Session
from schedora.core.enums import JobStatus, WorkerStatus


# Job metrics
jobs_created_total = Counter(
    'schedora_jobs_created_total',
    'Total number of jobs created',
    ['job_type']
)

jobs_succeeded_total = Counter(
    'schedora_jobs_succeeded_total',
    'Total number of successful jobs',
    ['job_type']
)

jobs_failed_total = Counter(
    'schedora_jobs_failed_total',
    'Total number of failed jobs',
    ['job_type']
)

jobs_retrying_total = Counter(
    'schedora_jobs_retrying_total',
    'Total number of jobs being retried',
    ['job_type']
)

job_duration_seconds = Histogram(
    'schedora_job_duration_seconds',
    'Job execution duration in seconds',
    ['job_type', 'status'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Worker metrics
workers_active = Gauge(
    'schedora_workers_active',
    'Number of active workers'
)

workers_stale = Gauge(
    'schedora_workers_stale',
    'Number of stale workers'
)

worker_jobs_current = Gauge(
    'schedora_worker_jobs_current',
    'Current number of jobs being processed by worker',
    ['worker_id']
)

# Queue metrics
queue_length = Gauge(
    'schedora_queue_length',
    'Number of jobs in the queue',
    ['queue_name']
)

queue_dlq_length = Gauge(
    'schedora_queue_dlq_length',
    'Number of jobs in the dead letter queue',
    ['queue_name']
)

queue_enqueued_total = Counter(
    'schedora_queue_enqueued_total',
    'Total number of jobs enqueued',
    ['queue_name']
)

queue_dequeued_total = Counter(
    'schedora_queue_dequeued_total',
    'Total number of jobs dequeued',
    ['queue_name']
)

# System info
system_info = Info(
    'schedora_system',
    'Schedora system information'
)


def update_worker_metrics(db: Session) -> None:
    """
    Update worker gauge metrics from database.

    Args:
        db: Database session
    """
    from schedora.repositories.worker_repository import WorkerRepository

    repo = WorkerRepository(db)

    # Count active workers
    active_workers = repo.get_by_status(WorkerStatus.ACTIVE)
    workers_active.set(len(active_workers))

    # Count stale workers
    stale_workers = repo.get_by_status(WorkerStatus.STALE)
    workers_stale.set(len(stale_workers))


def update_queue_metrics(queue: Optional["RedisQueue"] = None) -> None:
    """
    Update queue gauge metrics.

    Args:
        queue: Optional RedisQueue instance
    """
    if not queue:
        return

    queue_length.labels(queue_name="jobs").set(queue.get_queue_length())
    queue_dlq_length.labels(queue_name="jobs").set(queue.get_dlq_length())


def record_job_created(job_type: str) -> None:
    """Record job creation metric."""
    jobs_created_total.labels(job_type=job_type).inc()


def record_job_succeeded(job_type: str, duration: float) -> None:
    """Record job success metric."""
    jobs_succeeded_total.labels(job_type=job_type).inc()
    job_duration_seconds.labels(job_type=job_type, status="success").observe(duration)


def record_job_failed(job_type: str, duration: float) -> None:
    """Record job failure metric."""
    jobs_failed_total.labels(job_type=job_type).inc()
    job_duration_seconds.labels(job_type=job_type, status="failed").observe(duration)


def record_job_retrying(job_type: str) -> None:
    """Record job retry metric."""
    jobs_retrying_total.labels(job_type=job_type).inc()


def record_queue_enqueue(queue_name: str = "jobs") -> None:
    """Record job enqueued to queue."""
    queue_enqueued_total.labels(queue_name=queue_name).inc()


def record_queue_dequeue(queue_name: str = "jobs") -> None:
    """Record job dequeued from queue."""
    queue_dequeued_total.labels(queue_name=queue_name).inc()


def init_system_info(version: str) -> None:
    """
    Initialize system information metric.

    Args:
        version: Application version
    """
    system_info.info({
        'version': version,
        'name': 'Schedora'
    })
