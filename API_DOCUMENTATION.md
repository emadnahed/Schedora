# Schedora API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`

## Table of Contents
- [Overview](#overview)
- [Response Format](#response-format)
- [Response Codes](#response-codes)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Jobs](#jobs)
  - [Workflows](#workflows)
- [Error Handling](#error-handling)

---

## Overview

Schedora is a distributed job orchestration platform that provides:
- **Job Management**: Create, monitor, and cancel jobs
- **DAG Workflows**: Define complex job dependencies
- **Retry Mechanisms**: Configurable retry policies (fixed, exponential, jitter)
- **Atomic Scheduling**: Concurrent-safe job claiming
- **Idempotency**: Guaranteed unique job execution

---

## Response Format

All API responses follow a standardized format:

### Success Response
```json
{
    "data": { ... },
    "code": "JOB_0001",
    "httpStatus": "CREATED",
    "description": "Job created successfully"
}
```

### Error Response
```json
{
    "data": null,
    "code": "JOB_4001",
    "httpStatus": "NOT_FOUND",
    "description": "Job with ID {job_id} not found"
}
```

**Fields:**
- `data`: Response payload (object for success, null for errors)
- `code`: Response code (e.g., JOB_0001, WF_4001)
- `httpStatus`: HTTP status text (CREATED, OK, NOT_FOUND, etc.)
- `description`: Human-readable message

---

## Response Codes

### Job Endpoints

**Success Codes:**
- `JOB_0001` - Job created successfully (201)
- `JOB_0002` - Job retrieved successfully (200)
- `JOB_0003` - Job canceled successfully (200)

**Error Codes:**
- `JOB_4001` - Job not found (404)
- `JOB_4002` - Duplicate idempotency key (409)
- `JOB_4003` - Invalid state transition (400)

### Workflow Endpoints

**Success Codes:**
- `WF_0001` - Workflow created successfully (201)
- `WF_0002` - Workflow retrieved successfully (200)
- `WF_0003` - Workflow status retrieved successfully (200)
- `WF_0004` - Job added to workflow successfully (200)

**Error Codes:**
- `WF_4001` - Workflow not found (404)
- `WF_4002` - Duplicate workflow name (409)

### Health Endpoint

**Success Codes:**
- `HEALTH_0001` - Health check completed successfully (200)

---

## Authentication

Currently, the API does not require authentication. This will be added in future phases.

---

## Endpoints

### Health Check

#### Check Service Health
Get the health status of the Schedora service and its dependencies.

**Endpoint:** `GET /api/v1/health`

**cURL:**
```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Response (200 OK):**
```json
{
    "data": {
        "status": "healthy",
        "database": "connected"
    },
    "code": "HEALTH_0001",
    "httpStatus": "OK",
    "description": "Health check completed successfully"
}
```

---

### Jobs

#### 1. Create Job
Create a new job with specified type, payload, and configuration.

**Endpoint:** `POST /api/v1/jobs`

**Request Body:**
```json
{
    "type": "string",                    // Required: Job type identifier
    "payload": {},                       // Optional: Job-specific data (JSONB)
    "idempotency_key": "string",        // Required: Unique key for idempotency
    "priority": 5,                       // Optional: Priority (0-10, default: 5)
    "max_retries": 3,                   // Optional: Max retry attempts (default: 3)
    "timeout": 3600,                    // Optional: Timeout in seconds (default: 3600)
    "retry_policy": "exponential",      // Optional: fixed|exponential|jitter (default: exponential)
    "scheduled_at": "2025-01-01T12:00:00Z"  // Optional: Schedule for future execution
}
```

**Minimal cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "email_notification",
    "idempotency_key": "email-123"
  }'
```

**Full cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "data_processing",
    "payload": {
        "source": "s3://bucket/data.csv",
        "destination": "postgres://table"
    },
    "idempotency_key": "data-proc-2025-01-01-001",
    "priority": 8,
    "max_retries": 5,
    "timeout": 7200,
    "retry_policy": "jitter",
    "scheduled_at": "2025-01-01T08:00:00Z"
  }'
```

**Response (201 CREATED):**
```json
{
    "data": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "data_processing",
        "payload": {
            "source": "s3://bucket/data.csv",
            "destination": "postgres://table"
        },
        "status": "PENDING",
        "priority": 8,
        "max_retries": 5,
        "retry_count": 0,
        "retry_policy": "jitter",
        "timeout": 7200,
        "idempotency_key": "data-proc-2025-01-01-001",
        "scheduled_at": "2025-01-01T08:00:00Z",
        "worker_id": null,
        "started_at": null,
        "completed_at": null,
        "error_message": null,
        "error_details": null,
        "result": null,
        "created_at": "2024-12-23T10:30:00Z",
        "updated_at": "2024-12-23T10:30:00Z"
    },
    "code": "JOB_0001",
    "httpStatus": "CREATED",
    "description": "Job created successfully"
}
```

**Error Response - Duplicate Idempotency Key (409 CONFLICT):**
```json
{
    "detail": {
        "data": null,
        "code": "JOB_4002",
        "httpStatus": "CONFLICT",
        "description": "Job with idempotency key 'email-123' already exists"
    }
}
```

**Error Response - Validation Error (422 UNPROCESSABLE ENTITY):**
```bash
# Missing required field
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "test"
  }'
```

---

#### 2. Get Job by ID
Retrieve job details by job ID.

**Endpoint:** `GET /api/v1/jobs/{job_id}`

**cURL:**
```bash
curl -X GET http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**
```json
{
    "data": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "data_processing",
        "status": "RUNNING",
        "payload": {
            "source": "s3://bucket/data.csv",
            "destination": "postgres://table"
        },
        "priority": 8,
        "max_retries": 5,
        "retry_count": 0,
        "retry_policy": "jitter",
        "timeout": 7200,
        "idempotency_key": "data-proc-2025-01-01-001",
        "scheduled_at": "2025-01-01T08:00:00Z",
        "worker_id": "worker-abc123",
        "started_at": "2025-01-01T08:00:05Z",
        "completed_at": null,
        "error_message": null,
        "error_details": null,
        "result": null,
        "created_at": "2024-12-23T10:30:00Z",
        "updated_at": "2025-01-01T08:00:05Z"
    },
    "code": "JOB_0002",
    "httpStatus": "OK",
    "description": "Job retrieved successfully"
}
```

**Error Response - Job Not Found (404 NOT FOUND):**
```json
{
    "detail": {
        "data": null,
        "code": "JOB_4001",
        "httpStatus": "NOT_FOUND",
        "description": "Job with ID 550e8400-e29b-41d4-a716-446655440000 not found"
    }
}
```

---

#### 3. Cancel Job
Cancel a running or pending job.

**Endpoint:** `POST /api/v1/jobs/{job_id}/cancel`

**cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/cancel
```

**Response (200 OK):**
```json
{
    "data": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "CANCELED",
        "message": "Job 550e8400-e29b-41d4-a716-446655440000 has been canceled"
    },
    "code": "JOB_0003",
    "httpStatus": "OK",
    "description": "Job canceled successfully"
}
```

**Error Response - Invalid Transition (400 BAD REQUEST):**
```json
{
    "detail": {
        "data": null,
        "code": "JOB_4003",
        "httpStatus": "BAD_REQUEST",
        "description": "Cannot transition from SUCCESS to CANCELED"
    }
}
```

**Error Response - Job Not Found (404 NOT FOUND):**
```json
{
    "detail": {
        "data": null,
        "code": "JOB_4001",
        "httpStatus": "NOT_FOUND",
        "description": "Job with ID 550e8400-e29b-41d4-a716-446655440000 not found"
    }
}
```

---

### Workflows

#### 1. Create Workflow
Create a new workflow to organize jobs into a DAG.

**Endpoint:** `POST /api/v1/workflows`

**Request Body:**
```json
{
    "name": "string",              // Required: Unique workflow name
    "description": "string",       // Optional: Workflow description
    "config": {}                   // Optional: JSONB configuration
}
```

**Minimal cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_etl_pipeline"
  }'
```

**Full cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_etl_pipeline",
    "description": "Daily ETL pipeline for customer data",
    "config": {
        "timeout": 14400,
        "notifications": {
            "email": "ops@example.com",
            "slack": "#data-pipeline"
        },
        "retry_policy": "exponential"
    }
  }'
```

**Response (201 CREATED):**
```json
{
    "data": {
        "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "daily_etl_pipeline",
        "description": "Daily ETL pipeline for customer data",
        "config": {
            "timeout": 14400,
            "notifications": {
                "email": "ops@example.com",
                "slack": "#data-pipeline"
            },
            "retry_policy": "exponential"
        }
    },
    "code": "WF_0001",
    "httpStatus": "CREATED",
    "description": "Workflow created successfully"
}
```

**Error Response - Duplicate Name (409 CONFLICT):**
```json
{
    "detail": {
        "data": null,
        "code": "WF_4002",
        "httpStatus": "CONFLICT",
        "description": "Workflow with name 'daily_etl_pipeline' already exists"
    }
}
```

---

#### 2. Get Workflow by ID
Retrieve workflow details by workflow ID.

**Endpoint:** `GET /api/v1/workflows/{workflow_id}`

**cURL:**
```bash
curl -X GET http://localhost:8000/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000
```

**Response (200 OK):**
```json
{
    "data": {
        "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "daily_etl_pipeline",
        "description": "Daily ETL pipeline for customer data",
        "config": {
            "timeout": 14400,
            "notifications": {
                "email": "ops@example.com",
                "slack": "#data-pipeline"
            },
            "retry_policy": "exponential"
        }
    },
    "code": "WF_0002",
    "httpStatus": "OK",
    "description": "Workflow retrieved successfully"
}
```

**Error Response - Workflow Not Found (404 NOT FOUND):**
```json
{
    "detail": {
        "data": null,
        "code": "WF_4001",
        "httpStatus": "NOT_FOUND",
        "description": "Workflow with ID 123e4567-e89b-12d3-a456-426614174000 not found"
    }
}
```

---

#### 3. Add Job to Workflow
Add an existing job to a workflow.

**Endpoint:** `POST /api/v1/workflows/{workflow_id}/jobs`

**Request Body:**
```json
{
    "job_id": "uuid"  // Required: Job UUID to add
}
```

**cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response (200 OK):**
```json
{
    "data": {
        "message": "Job added to workflow successfully"
    },
    "code": "WF_0004",
    "httpStatus": "OK",
    "description": "Job added to workflow successfully"
}
```

**Error Response - Workflow Not Found (404 NOT FOUND):**
```json
{
    "detail": {
        "data": null,
        "code": "WF_4001",
        "httpStatus": "NOT_FOUND",
        "description": "Workflow with ID 123e4567-e89b-12d3-a456-426614174000 not found"
    }
}
```

---

#### 4. Get Workflow Status
Get execution status of a workflow with job statistics.

**Endpoint:** `GET /api/v1/workflows/{workflow_id}/status`

**cURL:**
```bash
curl -X GET http://localhost:8000/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000/status
```

**Response (200 OK):**
```json
{
    "data": {
        "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
        "workflow_name": "daily_etl_pipeline",
        "total_jobs": 10,
        "completed_jobs": 7,
        "failed_jobs": 0,
        "running_jobs": 3,
        "status": "RUNNING"
    },
    "code": "WF_0003",
    "httpStatus": "OK",
    "description": "Workflow status retrieved successfully"
}
```

**Workflow Status Values:**
- `PENDING` - No jobs have started
- `RUNNING` - At least one job is running or scheduled
- `COMPLETED` - All jobs completed successfully
- `FAILED` - At least one job failed

**Error Response - Workflow Not Found (404 NOT FOUND):**
```json
{
    "detail": {
        "data": null,
        "code": "WF_4001",
        "httpStatus": "NOT_FOUND",
        "description": "Workflow with ID 123e4567-e89b-12d3-a456-426614174000 not found"
    }
}
```

---

## Error Handling

### HTTP Status Codes
- `200 OK` - Request successful
- `201 CREATED` - Resource created successfully
- `400 BAD REQUEST` - Invalid request (e.g., invalid state transition)
- `404 NOT FOUND` - Resource not found
- `409 CONFLICT` - Duplicate resource (e.g., idempotency key, workflow name)
- `422 UNPROCESSABLE ENTITY` - Validation error (missing required fields, invalid types)
- `500 INTERNAL SERVER ERROR` - Server error

### Error Response Format
All errors follow the standardized format with `detail` containing error information:

```json
{
    "detail": {
        "data": null,
        "code": "ERROR_CODE",
        "httpStatus": "HTTP_STATUS_TEXT",
        "description": "Detailed error message"
    }
}
```

### Common Validation Errors

**Missing Required Field:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "test"
  }'

# Returns 422 with validation details
```

**Invalid Priority Range:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "test",
    "idempotency_key": "key-1",
    "priority": 15
  }'

# Returns 422: priority must be between 0-10
```

**Invalid UUID Format:**
```bash
curl -X GET http://localhost:8000/api/v1/jobs/not-a-uuid

# Returns 422: invalid UUID format
```

---

## Complete Workflow Example

This example demonstrates creating a complete workflow with job dependencies:

```bash
# 1. Create a workflow
WORKFLOW_ID=$(curl -s -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "data_pipeline_example",
    "description": "Example ETL pipeline"
  }' | jq -r '.data.workflow_id')

echo "Created workflow: $WORKFLOW_ID"

# 2. Create first job (data extraction)
JOB1_ID=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "extract_data",
    "payload": {"source": "api.example.com"},
    "idempotency_key": "extract-001",
    "priority": 10
  }' | jq -r '.data.job_id')

echo "Created job 1: $JOB1_ID"

# 3. Create second job (data transformation)
JOB2_ID=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "transform_data",
    "payload": {"format": "parquet"},
    "idempotency_key": "transform-001",
    "priority": 8
  }' | jq -r '.data.job_id')

echo "Created job 2: $JOB2_ID"

# 4. Create third job (data loading)
JOB3_ID=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "load_data",
    "payload": {"destination": "warehouse"},
    "idempotency_key": "load-001",
    "priority": 5
  }' | jq -r '.data.job_id')

echo "Created job 3: $JOB3_ID"

# 5. Add jobs to workflow
curl -X POST http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/jobs \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"$JOB1_ID\"}"

curl -X POST http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/jobs \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"$JOB2_ID\"}"

curl -X POST http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/jobs \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"$JOB3_ID\"}"

# 6. Check workflow status
curl -X GET http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/status

# 7. Get individual job status
curl -X GET http://localhost:8000/api/v1/jobs/$JOB1_ID
curl -X GET http://localhost:8000/api/v1/jobs/$JOB2_ID
curl -X GET http://localhost:8000/api/v1/jobs/$JOB3_ID
```

---

## Job State Machine

Jobs follow this state transition flow:

```
PENDING → SCHEDULED → RUNNING → SUCCESS
                         ↓          ↓
                      RETRYING → FAILED → DEAD

CANCELED (from any non-terminal state)
```

**States:**
- `PENDING` - Job created, waiting to be scheduled
- `SCHEDULED` - Job claimed by scheduler, ready for execution
- `RUNNING` - Job currently executing on a worker
- `SUCCESS` - Job completed successfully (terminal)
- `FAILED` - Job failed, may be retried
- `RETRYING` - Job failed but will be retried
- `DEAD` - Job exhausted all retries (terminal)
- `CANCELED` - Job manually canceled (terminal)

**Terminal States:** SUCCESS, DEAD, CANCELED

---

## Retry Policies

### Fixed Retry
Constant delay between retries.
- Delay: `base_delay` seconds (default: 60s)

### Exponential Backoff
Exponentially increasing delay.
- Delay: `base_delay * 2^retry_count`
- Capped at `max_delay` (default: 3600s)

### Jitter Backoff
Exponential with random jitter.
- Delay: `(base_delay * 2^retry_count) + random(0, 50%)`
- Prevents thundering herd problem

---

## Support

For issues or questions, please refer to the project repository or documentation.

**API Version:** 1.0.0
**Last Updated:** December 23, 2024
