# REST API Reference — TraceTest AI

## 1. Overview

TraceTest AI exposes a fully typed REST API conforming to OpenAPI 3.1.0 specifications. All API endpoints are prefixed with `/api/v1` and return JSON payloads.

---

## 2. Core API Endpoints

### 2.1 Projects
- `GET /api/v1/projects`: List accessible projects with calculated coverage and defect statistics.
- `POST /api/v1/projects`: Create a new project workspace.
- `POST /api/v1/projects/import-repo`: Ingest an external repository (e.g. EchoBox), extract architecture, and formulate requirements.
- `GET /api/v1/projects/{id}`: Retrieve project detail including modules, environments, and members.
- `PATCH /api/v1/projects/{id}`: Update project metadata or archive workspace.

### 2.2 Requirements
- `GET /api/v1/projects/{id}/requirements`: List requirements for a project with clause counts and status.
- `POST /api/v1/projects/{id}/requirements`: Create a new versioned requirement.
- `GET /api/v1/requirements/{id}`: Retrieve requirement detail, active version, clauses, and ambiguity flags.
- `PATCH /api/v1/requirements/{id}`: Update requirement text, creating an immutable `RequirementVersion` snapshot.
- `POST /api/v1/requirements/{id}/analyse`: Trigger AI requirement analysis, clause splitting, and rule extraction.
- `POST /api/v1/requirements/{id}/generate-acs`: Trigger AI acceptance criteria generation.

### 2.3 Test Cases
- `GET /api/v1/projects/{id}/tests`: List test cases with filter parameters (type, priority, status).
- `POST /api/v1/projects/{id}/requirements/{req_id}/generate-tests`: Trigger AI test generation.
- `GET /api/v1/tests/{id}`: Retrieve test case detail, script source, and validation status.
- `PATCH /api/v1/tests/{id}`: Update test script or metadata (creates `TestCaseVersion`).
- `POST /api/v1/tests/{id}/review`: Review test case (`approve`, `reject`, `request_changes`).

### 2.4 Executions
- `GET /api/v1/projects/{id}/executions`: List executions with duration and pass/fail counts.
- `POST /api/v1/projects/{id}/executions`: Queue a test suite execution against a target environment.
- `GET /api/v1/executions/{key}`: Retrieve execution outcomes, per-test results, and log excerpts.
- `GET /api/v1/executions/{key}/artifacts/{kind}`: Download execution artifacts (logs, JUnit XML, screenshots).

### 2.5 Defects
- `GET /api/v1/projects/{id}/defects`: List defects with severity, priority, and status.
- `POST /api/v1/projects/{id}/defects`: Log a new defect linked to a failed execution result.
- `GET /api/v1/defects/{id}`: Retrieve defect detail, reproduction steps, and AI root-cause analysis.
- `PATCH /api/v1/defects/{id}`: Transition defect status (`triaged`, `in_progress`, `fixed`, `verified`).
- `POST /api/v1/defects/{id}/retest`: Trigger automated retest execution against candidate fix environment.

### 2.6 Settings & Diagnostics
- `GET /api/v1/settings/llm/status`: Return live AI provider health, active models, and circuit breaker states.
- `POST /api/v1/settings/llm/test`: Perform diagnostic test ping against specified provider (`groq`, `gemini`, `ollama`).

---

## 3. Standard Response Format & Error Handling

### Standard Error Envelope
All errors return consistent JSON payloads:
```json
{
  "error": "Bad Request",
  "detail": "Room name cannot exceed 100 characters",
  "status_code": 400
}
```

### HTTP Status Code Conventions
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Input validation error.
- `401 Unauthorized`: Missing or invalid credentials.
- `403 Forbidden`: Caller lacks authorization for entity.
- `404 Not Found`: Target resource does not exist.
- `409 Conflict`: Business rule violation (e.g. duplicate project key).
- `410 Gone`: Ephemeral resource has reached its expiration ceiling.
- `413 Payload Too Large`: Request body exceeds 64KB limit.
- `500 Internal Server Error`: Unhandled server exception.
