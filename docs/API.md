# TraceTest AI — REST API Reference

The TraceTest AI backend exposes an OpenAPI 3.1 compliant REST API serving the React Single-Page Application and CI/CD automation pipelines.

- **Base URL**: `/api/v1`
- **Protocol**: HTTP/1.1 or HTTP/2 over TLS
- **Data Format**: `application/json` (UTF-8)
- **OpenAPI Specification**: `docs/openapi.json` (auto-exported via `scripts/export_openapi.py`)

---

## 1. Request & Response Conventions

### 1.1 Headers
| Header | Required | Purpose |
|---|---|---|
| `Content-Type` | Yes (for JSON bodies) | Must be `application/json`. |
| `X-CSRF-Token` | Yes (for mutating methods) | Required on `POST`, `PUT`, `PATCH`, `DELETE`. Must match active session token. |
| `X-Trace-Id` | Optional | Returned on every response (UUID4) for distributed log correlation. |
| `Authorization` | Optional | `Bearer <token>` supported for CI endpoints (`/api/v1/ci/results`). |

### 1.2 Standard Error Envelope
All error responses (4xx, 5xx) adhere to a deterministic JSON schema:

```json
{
  "error": {
    "code": "conflict",
    "message": "Defect DEF-PAY-0001 cannot transition to verified without a passing retest execution on a fix build.",
    "status": 409,
    "details": {},
    "trace_id": "4a7b5d12-9c3f-4e8b-8a21-91d8f1e2c3b4"
  }
}
```

### 1.3 Pagination & Sorting
List endpoints accept standard pagination query parameters:
- `page`: 1-based page index (default: `1`).
- `page_size`: Number of records per page (default: `25`, max: `100`).
- `sort`: Column name to sort by.
- `order`: Sort direction (`asc` or `desc`, default: `desc`).
- `q`: Case-insensitive substring search query.

Pagination response format:
```json
{
  "items": [ ... ],
  "total": 68,
  "page": 1,
  "page_size": 25,
  "pages": 3
}
```

---

## 2. Authentication & Session Endpoints

### `POST /api/v1/auth/login`
Authenticates a user using Argon2id password verification and establishes an HttpOnly session cookie.
- **Request Body**:
  ```json
  {
    "email": "qa.engineer@northwind-hcm.example",
    "password": "SecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "user": {
      "id": 2,
      "email": "qa.engineer@northwind-hcm.example",
      "full_name": "QA Engineer",
      "is_active": true
    },
    "roles": ["qa_engineer"],
    "csrf_token": "a1b2c3d4e5f6...",
    "session_expires_at": "2026-11-06T11:00:00Z"
  }
  ```
- **Cookies Set**: `tracetest_session` (`HttpOnly`, `SameSite=Lax`, `Path=/`).

### `POST /api/v1/auth/logout`
Revokes the active session token in SQLite and clears the session cookie.
- **Response**: `200 OK` `{"status": "signed_out"}`

### `GET /api/v1/auth/me`
Returns the currently authenticated user identity, role assignments, and permissions.

---

## 3. Project Management Endpoints

### `GET /api/v1/projects`
Lists all active projects accessible to the authenticated principal.

### `GET /api/v1/projects/{id}`
Returns details for a project including its modules, configured environments, and team members.

### `GET /api/v1/projects/{id}/summary`
Computes live quality metrics for the project (requirements count, test count, pass rate, open defects).

---

## 4. Requirements & AI Analysis Endpoints

### `GET /api/v1/requirements`
Lists requirements with optional filtering by `project_id`, `status` (`draft`, `analysed`, `tests_generated`), `priority`, and `category`.

### `POST /api/v1/requirements`
Creates a new draft requirement.
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "title": "Shift Differential Rules",
    "description": "Evening shift workers receive a 5% differential. Night shift workers receive 10%.",
    "business_objective": "Compensate off-hours labor accurately.",
    "priority": "high",
    "category": "functional",
    "module_id": 1
  }
  ```

### `POST /api/v1/requirements/upload`
Uploads a requirement document (`.txt`, `.md`, or `.pdf` up to 2 MB), sanitizes the text, extracts clauses, and saves requirement v1.
- **Content-Type**: `multipart/form-data`
- **Fields**: `file` (binary), `project_id` (int), `title` (string), `priority` (string), `module_id` (optional int).

### `POST /api/v1/requirements/{id}/analyse`
Initiates asynchronous clause extraction and ambiguity analysis via LangGraph.
- **Response** (`202 Accepted`): `{"requirement_id": 1, "run_id": 12}`

### `POST /api/v1/requirements/{id}/generate-tests`
Runs the complete requirement graph: extracts clauses, generates acceptance criteria with verbatim source quotes, generates executable test cases, validates AST allowlists, and stops before `human_review`.
- **Response** (`202 Accepted`): `{"requirement_id": 1, "run_id": 13}`

---

## 5. Test Management & Review Endpoints

### `GET /api/v1/tests`
Lists test cases with filters (`project_id`, `requirement_id`, `status`, `validation_status`, `automation`).

### `POST /api/v1/tests/{id}/review`
Submits a review decision for a test case (`approve`, `reject`, `request_changes`).
- **Authorization**: Requires `test.review` permission. Authors cannot approve their own tests.
- **Request Body**:
  ```json
  {
    "decision": "approve",
    "comment": "Verified assertions against clause C1."
  }
  ```

### `POST /api/v1/tests/review/bulk`
Applies a review decision to multiple tests in a single transaction.
- **Request Body**:
  ```json
  {
    "test_ids": [14, 15, 16],
    "decision": "approve",
    "comment": "Bulk approval for approved v1.1 regression suite."
  }
  ```

---

## 6. Execution & Sandbox Endpoints

### `POST /api/v1/executions`
Spawns an asynchronous sandboxed test run for an approved test suite.
- **Request Body**:
  ```json
  {
    "suite_id": 1,
    "environment_id": 2
  }
  ```
- **Response** (`202 Accepted`): `{"execution_id": 45, "run_id": 22}`

### `GET /api/v1/executions/{id}`
Returns execution summary, overall status (`running`, `completed`, `failed`), durations, and outcome counts.

### `GET /api/v1/executions/{id}/results`
Returns individual test case results (`passed`, `failed`, `error`, `timed_out`), stack traces, and stdout.

### `GET /api/v1/executions-compare?a={id1}&b={id2}`
Computes an automated regression diff between two execution runs, identifying newly passing and regressed tests.

---

## 7. Defect Lifecycle Endpoints

### `GET /api/v1/defects`
Lists tracked defects with filters (`status`, `severity`, `priority`, `project_id`, `open_only`).

### `POST /api/v1/defects`
Logs a new defect manually or links it to a failed execution result.

### `POST /api/v1/defects/{id}/transition`
Transitions a defect across its state machine (`open` → `triaged` → `assigned` → `in_progress` → `fixed` → `ready_for_retest` → `verified` → `closed`).
- **Enforcement**: Transition to `verified` strictly requires a linked passing retest execution on a fix build.

### `POST /api/v1/defects/{id}/retest`
Triggers an automated single-test verification run against a candidate fix environment.

---

## 8. AI Evaluations & Quality Analytics

### `GET /api/v1/evaluations`
Lists historical AI evaluation runs with provider, model, aggregate scores, and timestamp.

### `POST /api/v1/evaluations/run`
Executes the 10 golden evaluation scenarios over a chosen provider (`groq`, `gemini`, or `mock`).
- **Request Body**: `{"provider": "groq"}`
- **Response** (`202 Accepted`): `{"eval_run_id": 3, "run_id": 25}`

### `GET /api/v1/analytics/dashboard`
Returns live calculated KPIs (coverage, pass rates, defect counts, trends, and charts).

### `GET /api/v1/analytics/traceability`
Returns the complete requirements-to-test traceability matrix with coverage flags and gap indicators.

---

## 9. System Administration & Integrity

### `POST /api/v1/admin/backup`
Performs an online, zero-downtime hot backup of `tracetest.db` using SQLite backup API and runs an integrity check.

### `GET /api/v1/config`
Returns environment configuration, active AI provider status (with safe, masked credential indicators), and sandbox limits.
