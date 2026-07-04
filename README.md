# Checkflow

Workflow engine focused on validating HTTP flows in distributed systems.
A plan defines ordered steps and, when executed, creates an `Execution` composed
of multiple `StepExecutions`. Executions are asynchronous and event-driven.

## Project Status

The MVP backend is implemented and under active development.

### MVP Scope

* [x] Plan CRUD
* [x] CRUD for steps associated with plans
* [x] Automatic sequence assignment and reordering
* [x] Sequential plan execution
* [x] Execution history and results
* [x] Variables and extractions between steps
* [x] Scheduling and asynchronous execution
* [x] Cancellation and retry
* [x] Real-time WebSocket
* [ ] React dashboard

### Conceptual Model

```text
Plan
  └── Execution
        ├── StepExecution 1
        ├── StepExecution 2
        ├── StepExecution 3
        └── Variables
```

* `Plan`: reusable definition of the flow and its steps;
* `Execution`: a concrete execution of a plan;
* `StepExecution`: the result of executing a step within an `Execution`;
* `Variables`: isolated context shared between the steps of the same execution.

## Architecture

The backend uses a single image, and Honcho starts the processes defined in the `Procfile`:

* `api`: CRUD and execution requests using FastAPI;
* `scheduler`: turns scheduled events into execution requests;
* `dispatcher`: consumes requests from Kafka and creates Celery tasks;
* `celery`: executes steps in the background;
* `realtime`: streams progress through WebSocket and receives commands.

Kafka acts as the event bus through the `checkflow.execution-events` topic.
Independent consumer groups receive the same stream. Redis is used as a cache for
the latest state of each execution and as the Celery broker/backend. PostgreSQL stores
plans, steps, execution history, and the result of each request.

The one-shot `kafka-init` service creates the topic before allowing the backend to start.

## Running the Environment

Prerequisites: Docker with Compose.

```bash
cp .env.example .env
docker compose up --build
```

The `backend` container applies `alembic upgrade head` and runs `honcho start`.

Available services:

* API: http://localhost:8000
* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc
* OpenAPI JSON: http://localhost:8000/openapi.json
* WebSocket: `ws://localhost:8001/ws/plans/{plan_id}/executions`

To stop the environment:

```bash
docker compose down
```

Add `-v` only when you also want to delete local data.

## Local Development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
docker compose up -d postgres redis kafka
.venv/bin/alembic upgrade head
.venv/bin/honcho start
```

To run the API on the host machine, adjust `DATABASE_URL` to point to a PostgreSQL
instance accessible from outside the Compose network. The recommended way to start
the full stack is the `docker compose up --build` command from the previous section.

## API

### Plans

```text
POST   /plans
GET    /plans
GET    /plans/{plan_id}
PUT    /plans/{plan_id}
DELETE /plans/{plan_id}
```

### Steps

```text
POST   /plans/{plan_id}/steps
GET    /plans/{plan_id}/steps
GET    /plans/{plan_id}/steps/{step_id}
PUT    /plans/{plan_id}/steps/{step_id}
DELETE /plans/{plan_id}/steps/{step_id}
PATCH  /plans/{plan_id}/steps/reorder
```

### Executions

```text
POST   /plans/{plan_id}/executions
GET    /plans/{plan_id}/executions
GET    /plans/{plan_id}/executions/{execution_id}
POST   /plans/{plan_id}/executions/{execution_id}/cancel
POST   /plans/{plan_id}/executions/{execution_id}/retry
```

Step example:

```json
{
  "sequence": 1,
  "name": "Create order",
  "action": {
    "type": "http",
    "method": "POST",
    "url": "https://orders.example.com/orders",
    "body": {"product_id": 42},
    "timeout_seconds": 30
  },
  "assertions": [
    {"target": "status_code", "operator": "equals", "expected": 201},
    {"target": "body", "path": "status", "expected": "created"}
  ]
}
```

`sequence` is optional when creating a step. When omitted, the API uses the next
position in the plan. Reordering receives all steps with contiguous sequences:

```json
{"steps": [{"step_id": 2, "sequence": 1}, {"step_id": 1, "sequence": 2}]}
```

Immediate execution:

```bash
curl -X POST http://localhost:8000/plans/1/executions \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Future execution uses an ISO 8601 datetime with timezone:

```json
{"scheduled_for": "2026-06-28T18:00:00-03:00"}
```

### Variables Between StepExecutions

A step can declare values to be extracted from the response. During an `Execution`,
subsequent `StepExecutions` can use `{{variable}}` templates in the URL, headers,
body, and expected assertion values. Variables belong to the `Execution`, not to the
`Plan`, and are persisted in PostgreSQL.

Example login step that captures a token:

```json
{
  "name": "Login",
  "action": {
    "method": "POST",
    "url": "https://api.example.com/auth",
    "body": {"email": "qa@example.com", "password": "secret"}
  },
  "assertions": [{"target": "status_code", "expected": 200}],
  "extracts": {"access_token": "body.access_token"}
}
```

The next step reuses the value:

```json
{
  "name": "Get profile",
  "action": {
    "method": "GET",
    "url": "https://api.example.com/me",
    "headers": {"Authorization": "Bearer {{access_token}}"}
  },
  "assertions": [
    {"target": "status_code", "expected": 200},
    {"target": "body", "path": "email", "expected": "qa@example.com"}
  ]
}
```

The supported extraction sources are `body.nested.path`, `header.Header-Name`,
and `status_code`. It is also possible to provide initial variables when starting
an execution:

```json
{"variables": {"tenant": "acme"}}
```

## Realtime and Control

Connect to the WebSocket to follow an entire plan `Execution`. Events include
`plan_id`, `execution_id`, the current step, the number of completed steps, and the
total number of steps.

The next step is only enqueued after `step.execution.completed.v1`; a failure ends
the plan execution.

To control an execution, send:

```json
{"command": "stop", "execution_id": "uuid"}
```

or:

```json
{"command": "restart", "execution_id": "uuid"}
```

The command also becomes an event in Kafka. The dispatcher revokes or recreates the
Celery task.

## Database and Migrations

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
.venv/bin/alembic revision --autogenerate -m "description"
```

## Quality

```bash
.venv/bin/pyright
.venv/bin/pytest
RUN_INTEGRATION_TESTS=1 .venv/bin/pytest tests/integration -v --no-cov
```

Integration tests use Testcontainers and require Docker.
