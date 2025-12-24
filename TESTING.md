# Schedora Testing Guide

This document provides comprehensive information about testing in the Schedora project.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Runner Script](#test-runner-script)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)

## Quick Start

### Prerequisites

1. Ensure Docker services are running:
   ```bash
   docker-compose up -d
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Run All Tests

```bash
# Using pytest directly
pytest tests/ -v

# Using test runner script (recommended)
./run_tests.sh all
```

## Test Structure

The test suite is organized into three main categories:

```
tests/
├── unit/                    # Unit tests (117 tests)
│   ├── test_config.py
│   ├── test_database_adapter.py
│   ├── test_enums.py
│   ├── test_handler_registry.py
│   ├── test_handlers.py
│   ├── test_redis_client.py
│   ├── test_redis_queue.py
│   ├── test_retry_service.py
│   ├── test_schemas.py
│   └── test_state_machine.py
│
├── integration/             # Integration tests (190 tests)
│   ├── test_async_worker.py
│   ├── test_background_tasks.py
│   ├── test_database_adapter.py
│   ├── test_dependency_resolver.py
│   ├── test_error_paths.py
│   ├── test_heartbeat_service.py
│   ├── test_job_dependencies.py
│   ├── test_job_executor.py
│   ├── test_job_model.py
│   ├── test_job_repository.py
│   ├── test_job_service.py
│   ├── test_job_service_with_queue.py
│   ├── test_production_mode.py
│   ├── test_redis_integration.py
│   ├── test_redis_queue_integration.py
│   ├── test_scheduler.py
│   ├── test_worker_model.py
│   ├── test_worker_repository.py
│   ├── test_worker_with_queue.py
│   ├── test_workflow_model.py
│   ├── test_workflow_repository.py
│   └── test_workflow_service.py
│
└── api/                     # API tests (42 tests)
    ├── test_health_api.py
    ├── test_jobs_api.py
    ├── test_metrics_api.py
    ├── test_queue_api.py
    ├── test_worker_api.py
    └── test_workflows_api.py
```

### Test Categories

#### Unit Tests
- Fast, isolated tests with no external dependencies
- Mock database and Redis interactions
- Focus on individual functions/classes
- **Runtime:** ~5 seconds

#### Integration Tests
- Test interactions between components
- Use real database and Redis (test instances)
- Test workflows and complex scenarios
- **Runtime:** ~25 seconds

#### API Tests
- End-to-end HTTP API testing
- Use FastAPI TestClient
- Test request/response handling
- **Runtime:** ~3 seconds

## Running Tests

### Using Test Runner Script (Recommended)

The `run_tests.sh` script provides multiple testing options:

#### 1. Complete Test Suite
```bash
./run_tests.sh all
```
Runs all 349 tests with full coverage reporting.

#### 2. Quick Tests (No Coverage)
```bash
./run_tests.sh quick
```
Fast execution for rapid feedback during development.

#### 3. By Segment
```bash
# Unit tests only
./run_tests.sh segment unit

# Integration tests only
./run_tests.sh segment integration

# API tests only
./run_tests.sh segment api
```

#### 4. Individual Test File
```bash
./run_tests.sh file tests/unit/test_redis_queue.py
```

#### 5. Specific Test by Name
```bash
# Pattern matching
./run_tests.sh test job_service
./run_tests.sh test redis_queue
```

#### 6. By Marker
```bash
# Tests marked with @pytest.mark.unit
./run_tests.sh marker unit

# Tests marked with @pytest.mark.integration
./run_tests.sh marker integration

# Tests marked with @pytest.mark.api
./run_tests.sh marker api
```

#### 7. List Test Files
```bash
./run_tests.sh list
```

#### 8. Show Statistics
```bash
./run_tests.sh stats
```

### Using Pytest Directly

#### All Tests
```bash
pytest tests/ -v
```

#### Specific Directory
```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/api/ -v
```

#### Specific File
```bash
pytest tests/unit/test_redis_queue.py -v
```

#### Specific Test
```bash
pytest tests/unit/test_redis_queue.py::TestRedisQueue::test_enqueue -v
```

#### With Coverage
```bash
pytest tests/ --cov=src/schedora --cov-report=html
```

#### By Marker
```bash
pytest tests/ -m unit -v
pytest tests/ -m integration -v
pytest tests/ -m api -v
```

#### Failed Tests Only
```bash
pytest tests/ --lf  # Last failed
pytest tests/ --ff  # Failed first, then rest
```

#### Stop on First Failure
```bash
pytest tests/ -x
```

#### Parallel Execution (Faster)
```bash
pip install pytest-xdist
pytest tests/ -n auto  # Use all CPU cores
```

## Test Coverage

### Current Coverage

- **Total Coverage:** 94.59%
- **Target:** ≥90%
- **Total Tests:** 349

### Generate Coverage Report

```bash
# Terminal output
pytest tests/ --cov=src/schedora --cov-report=term-missing

# HTML report (opens in browser)
pytest tests/ --cov=src/schedora --cov-report=html
open htmlcov/index.html
```

### Coverage by Module

```bash
pytest tests/ --cov=src/schedora --cov-report=term-missing | grep "^src/"
```

### Missing Coverage

View uncovered lines:
```bash
pytest tests/ --cov=src/schedora --cov-report=term-missing | grep "Missing"
```

## Writing Tests

### Test Structure

```python
"""Test module docstring."""
import pytest


@pytest.mark.unit  # or integration, api
class TestClassName:
    """Test class docstring."""

    def test_descriptive_name(self, fixture_name):
        """Test function docstring - describe what it tests."""
        # Arrange
        expected = "value"

        # Act
        result = function_under_test()

        # Assert
        assert result == expected
```

### Common Fixtures

Defined in `tests/conftest.py`:

- `db_session` - Database session for tests
- `redis_client` - Redis client for tests
- `client` - FastAPI TestClient
- `sample_job` - Factory for creating test jobs
- `sample_worker` - Factory for creating test workers

### Example Unit Test

```python
"""Unit test example."""
import pytest
from schedora.services.redis_queue import RedisQueue


@pytest.mark.unit
class TestRedisQueue:
    """Test Redis queue functionality."""

    def test_enqueue_adds_job_to_queue(self, mock_redis):
        """Test that enqueue adds job to Redis sorted set."""
        # Arrange
        queue = RedisQueue(mock_redis)
        job_id = uuid4()
        priority = 10

        # Act
        queue.enqueue(job_id, priority)

        # Assert
        mock_redis.zadd.assert_called_once()
```

### Example Integration Test

```python
"""Integration test example."""
import pytest
from schedora.services.job_service import JobService
from schedora.api.schemas.job import JobCreate


@pytest.mark.integration
class TestJobService:
    """Test job service with real database."""

    def test_create_job_persists_to_database(self, db_session):
        """Test job creation writes to database."""
        # Arrange
        service = JobService(db_session)
        job_data = JobCreate(
            type="echo",
            payload={"test": "data"},
            idempotency_key="test-key-1"
        )

        # Act
        job = service.create_job(job_data)

        # Assert
        assert job.job_id is not None
        assert job.status == JobStatus.PENDING
```

### Example API Test

```python
"""API test example."""
import pytest


@pytest.mark.api
class TestJobsAPI:
    """Test job API endpoints."""

    def test_create_job_returns_201(self, client):
        """Test POST /api/v1/jobs returns 201 Created."""
        # Arrange
        payload = {
            "type": "echo",
            "payload": {"test": "data"},
            "idempotency_key": "test-1"
        }

        # Act
        response = client.post("/api/v1/jobs", json=payload)

        # Assert
        assert response.status_code == 201
        assert "job_id" in response.json()["data"]
```

### Async Tests

```python
"""Async test example."""
import pytest


@pytest.mark.asyncio
async def test_async_worker_executes_job(db_session):
    """Test async worker job execution."""
    # Arrange
    worker = AsyncWorker(db_session)

    # Act
    result = await worker.execute_job(job_id)

    # Assert
    assert result.status == "success"
```

## Test Markers

Available markers (configured in `pyproject.toml`):

- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (DB, Redis)
- `@pytest.mark.api` - API tests (HTTP endpoints)

Run specific markers:
```bash
pytest -m unit
pytest -m integration
pytest -m api
```

## Continuous Integration

### GitHub Actions (Recommended)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: schedora_pass
          POSTGRES_USER: schedora_user
          POSTGRES_DB: schedora_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest tests/ --cov=src/schedora --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
./run_tests.sh quick
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Tests Failing Due to Docker

Ensure Docker containers are running:
```bash
docker-compose ps
docker-compose up -d
```

### Database Connection Errors

Reset test database:
```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### Redis Connection Errors

Check Redis is accessible:
```bash
docker exec -it schedora_redis redis-cli ping
```

### Coverage Below Threshold

View missing coverage:
```bash
pytest tests/ --cov=src/schedora --cov-report=term-missing | grep "Missing"
```

### Slow Tests

Run with timing:
```bash
pytest tests/ --durations=10
```

Use parallel execution:
```bash
pytest tests/ -n auto
```

## Best Practices

1. **Write tests first** - Follow TDD methodology
2. **Keep tests independent** - No shared state between tests
3. **Use descriptive names** - Test name should describe what it tests
4. **One assertion concept per test** - Focus on single behavior
5. **Use fixtures** - Reuse common setup code
6. **Mock external services** - Use mocks for unit tests
7. **Test edge cases** - Include boundary conditions
8. **Maintain coverage** - Keep above 90% threshold
9. **Fast feedback** - Keep unit tests under 5 seconds
10. **Clean up** - Use fixtures for teardown

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
