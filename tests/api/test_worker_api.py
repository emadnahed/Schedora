"""API tests for worker endpoints."""
import pytest
from fastapi.testclient import TestClient
from schedora.repositories.worker_repository import WorkerRepository
from schedora.core.enums import WorkerStatus


def test_register_worker_success(client, db_session, redis_client):
    """Test successful worker registration."""
    request_data = {
        "worker_id": "test-worker-1",
        "hostname": "test-host",
        "pid": 12345,
        "max_concurrent_jobs": 5,
        "version": "1.0.0",
        "capabilities": {"gpu": True},
        "metadata": {"region": "us-west"},
    }

    response = client.post("/api/v1/workers/register", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["worker_id"] == "test-worker-1"
    assert data["hostname"] == "test-host"
    assert data["pid"] == 12345
    assert data["max_concurrent_jobs"] == 5
    assert data["status"] == WorkerStatus.ACTIVE.value
    assert data["current_job_count"] == 0

    # Verify Redis heartbeat key exists
    heartbeat_key = f"worker:test-worker-1:heartbeat"
    assert redis_client.exists(heartbeat_key)


def test_register_worker_duplicate(client, db_session, redis_client):
    """Test registering a worker with duplicate ID."""
    request_data = {
        "worker_id": "duplicate-worker",
        "hostname": "host1",
        "pid": 111,
        "max_concurrent_jobs": 3,
    }

    # First registration succeeds
    response1 = client.post("/api/v1/workers/register", json=request_data)
    assert response1.status_code == 201

    # Second registration with same ID should fail
    response2 = client.post("/api/v1/workers/register", json=request_data)
    assert response2.status_code == 400
    assert "Failed to register worker" in response2.json()["detail"]


def test_send_heartbeat_success(client, db_session, redis_client):
    """Test successful heartbeat."""
    # Register worker first
    register_data = {
        "worker_id": "heartbeat-worker",
        "hostname": "host",
        "pid": 999,
        "max_concurrent_jobs": 2,
    }
    client.post("/api/v1/workers/register", json=register_data)

    # Send heartbeat
    heartbeat_data = {"cpu_percent": 45.5, "memory_percent": 62.3}
    response = client.post(
        "/api/v1/workers/heartbeat-worker/heartbeat", json=heartbeat_data
    )

    assert response.status_code == 204

    # Verify worker metrics updated
    repo = WorkerRepository(db_session)
    worker = repo.get_by_id("heartbeat-worker")
    assert worker.cpu_percent == 45.5
    assert worker.memory_percent == 62.3


def test_send_heartbeat_worker_not_found(client, db_session, redis_client):
    """Test heartbeat for non-existent worker."""
    heartbeat_data = {"cpu_percent": 50.0}
    response = client.post(
        "/api/v1/workers/nonexistent-worker/heartbeat", json=heartbeat_data
    )

    assert response.status_code == 404
    assert "Worker nonexistent-worker not found" in response.json()["detail"]


def test_get_worker_success(client, db_session, redis_client):
    """Test getting worker details."""
    # Register worker
    register_data = {
        "worker_id": "get-worker-test",
        "hostname": "host",
        "pid": 555,
        "max_concurrent_jobs": 4,
    }
    client.post("/api/v1/workers/register", json=register_data)

    # Get worker
    response = client.get("/api/v1/workers/get-worker-test")

    assert response.status_code == 200
    data = response.json()
    assert data["worker_id"] == "get-worker-test"
    assert data["hostname"] == "host"
    assert data["pid"] == 555


def test_get_worker_not_found(client, db_session):
    """Test getting non-existent worker."""
    response = client.get("/api/v1/workers/nonexistent")

    assert response.status_code == 404
    assert "Worker nonexistent not found" in response.json()["detail"]


def test_list_workers_all(client, db_session, redis_client):
    """Test listing all workers."""
    # Register multiple workers
    for i in range(3):
        register_data = {
            "worker_id": f"worker-{i}",
            "hostname": f"host-{i}",
            "pid": 1000 + i,
            "max_concurrent_jobs": 5,
        }
        client.post("/api/v1/workers/register", json=register_data)

    # List all workers
    response = client.get("/api/v1/workers")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["workers"]) == 3


def test_list_workers_by_status_active(client, db_session, redis_client):
    """Test listing active workers only."""
    # Register workers
    for i in range(2):
        register_data = {
            "worker_id": f"active-worker-{i}",
            "hostname": "host",
            "pid": 2000 + i,
            "max_concurrent_jobs": 3,
        }
        client.post("/api/v1/workers/register", json=register_data)

    # Make one worker stale by removing its Redis heartbeat key
    redis_client.delete("worker:active-worker-1:heartbeat")
    repo = WorkerRepository(db_session)
    worker = repo.get_by_id("active-worker-1")
    worker.status = WorkerStatus.STALE
    db_session.commit()

    # List active workers only
    response = client.get("/api/v1/workers?status_filter=active")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["workers"][0]["worker_id"] == "active-worker-0"


def test_list_workers_by_status_stale(client, db_session, redis_client):
    """Test listing stale workers only."""
    # Register worker
    register_data = {
        "worker_id": "stale-test-worker",
        "hostname": "host",
        "pid": 3000,
        "max_concurrent_jobs": 2,
    }
    client.post("/api/v1/workers/register", json=register_data)

    # Make worker stale
    redis_client.delete("worker:stale-test-worker:heartbeat")
    repo = WorkerRepository(db_session)
    worker = repo.get_by_id("stale-test-worker")
    worker.status = WorkerStatus.STALE
    db_session.commit()

    # List stale workers
    response = client.get("/api/v1/workers?status_filter=stale")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["workers"][0]["worker_id"] == "stale-test-worker"
    assert data["workers"][0]["status"] == WorkerStatus.STALE.value


def test_get_worker_jobs(client, db_session, redis_client):
    """Test getting worker's current jobs."""
    from uuid import uuid4

    # Register worker
    register_data = {
        "worker_id": "jobs-test-worker",
        "hostname": "host",
        "pid": 4000,
        "max_concurrent_jobs": 5,
    }
    client.post("/api/v1/workers/register", json=register_data)

    # Assign some jobs to worker in Redis
    job1_id = uuid4()
    job2_id = uuid4()
    redis_client.sadd("worker:jobs-test-worker:jobs", str(job1_id), str(job2_id))

    # Get worker jobs
    response = client.get("/api/v1/workers/jobs-test-worker/jobs")

    assert response.status_code == 200
    data = response.json()
    assert data["worker_id"] == "jobs-test-worker"
    assert data["count"] == 2
    assert len(data["job_ids"]) == 2


def test_get_worker_jobs_not_found(client, db_session):
    """Test getting jobs for non-existent worker."""
    response = client.get("/api/v1/workers/nonexistent/jobs")

    assert response.status_code == 404


def test_deregister_worker_success(client, db_session, redis_client):
    """Test deregistering a worker."""
    # Register worker
    register_data = {
        "worker_id": "deregister-worker",
        "hostname": "host",
        "pid": 5000,
        "max_concurrent_jobs": 3,
    }
    client.post("/api/v1/workers/register", json=register_data)

    # Verify heartbeat key exists
    assert redis_client.exists("worker:deregister-worker:heartbeat")

    # Deregister worker
    response = client.post("/api/v1/workers/deregister-worker/deregister")

    assert response.status_code == 204

    # Verify worker marked as STOPPED
    repo = WorkerRepository(db_session)
    worker = repo.get_by_id("deregister-worker")
    assert worker.status == WorkerStatus.STOPPED

    # Verify Redis keys cleaned up
    assert not redis_client.exists("worker:deregister-worker:heartbeat")


def test_deregister_worker_not_found(client, db_session):
    """Test deregistering non-existent worker."""
    response = client.post("/api/v1/workers/nonexistent/deregister")

    assert response.status_code == 404
