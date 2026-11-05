# TraceTest AI — Production Readiness & Implementation Audit

**Audit Date**: 2026-11-06  
**Auditor**: Senior Quality & Security Engineering Organisation  
**Scope**: Codebase, SQLite Storage (`var/tracetest.db`), Git Commit History, Execution Sandbox, EchoBox Harness, AI Pipelines, and Documentation.  
**Target Repository Snapshot**: `var/repos/EchoBox`  
**EchoBox Target Commit SHA**: `b3740a62ad414a141e82146adafb47c4850fd782` on branch `main`  
*(Commit Message: `docs: sanitize AWS resource IDs and API endpoints from README and audit docs`)*

---

## 1. Executive Summary

A rigorous, independent verification of the repository, database, and previous reports was conducted. The previous session successfully seeded the EchoBox project into SQLite, executed a 21-test sandbox suite, and documented initial findings. However, a critical audit revealed that several capabilities were either hardcoded specifically for EchoBox, partially implemented, or reliant on unverified assumptions.

This audit provides an unvarnished technical assessment of verified vs unverified claims, identifies critical security and data model vulnerabilities, and establishes a prioritized remediation plan to upgrade TraceTest AI into a true multi-project software verification platform.

---

## 2. Claim-by-Claim Verification Ledger

| Reported Item | Audited Status | Empirical Evidence / Finding |
|---|---|---|
| **Repository Import Service** | **Partially Implemented** | `backend/app/services/repo_ingest.py` and `POST /api/v1/projects/import-repo` exist, but `import-repo` hardcodes a call to `ingest_echobox_project()`. Connecting a non-EchoBox repository clones the files but populates EchoBox requirements. |
| **EchoBox Ingestion into SQLite** | **Verified** | Project `ECHO` (id=5) exists in `var/tracetest.db`. Contains 8 modules, 2 environments, and full entity linkages. |
| **21 Requirements** | **Verified** | Exactly 21 rows in `requirements` table (`ECHO-REQ-001` through `ECHO-REQ-021`), mapped to `project_id=5`. |
| **62 Clauses** | **Verified** | Exactly 62 rows in `clauses` table linked across the 21 requirements. Each clause contains normalized text and analysis JSON. |
| **21 Acceptance Criteria** | **Verified** | Exactly 21 rows in `acceptance_criteria` table with source quotes and confidence scores. |
| **21 EchoBox Test Cases** | **Verified** | Exactly 21 automated test cases in `test_cases` table (`TC-ECHO-0001` through `TC-ECHO-0021`) with full Python/pytest scripts. |
| **In-Memory `echobox_harness`** | **Verified** | `echobox_harness/` directory contains `table.py` and `backend.py`. Conforms to `boto3` Table interface and dispatches all 13 EchoBox RPC actions. |
| **Sandbox Execution `EX-000001`** | **Verified** | Execution record `EX-000001` exists in `executions` table with status `passed`, 21 total, 21 passed, duration 1.92s. |
| **Live AWS Probe `EX-ECHO-LIVE-001`** | **Verified** | Probe recorded in `executions` with status `error`, duration 574ms. Live endpoint returns HTTP 500 (`{"error": "Internal server error"}`). |
| **5 Defects (`DEF-ECHO-001` – `005`)** | **Verified** | 5 defects present in `defects` table for `project_id=5` (`DEF-ECHO-001` through `DEF-ECHO-005`). |
| **Playwright Screenshots** | **Verified** | Screenshots exist on disk at `docs/screenshots/echobox/echobox-frontend-landing.png` (193 KB) and `echobox-join-validation.png` (205 KB). |
| **Groq / Gemini AI Evaluation** | **Verified** | Runs 3 (Groq, completed) and 4 (Gemini, degraded due to quota) are stored in `eval_runs` table in `var/tracetest.db`. |
| **26 Documentation Files** | **Verified** | All 26 markdown documents present in `docs/` and verified on disk. |
| **Git Commits & Remote Push** | **Verified** | Commits `ab1596e`, `da814ce`, `7aff6b8` verified in local git log and pushed to `https://github.com/sohan10012/TEAM3.git` on `master`. |

---

## 3. Critical Security Findings

### SEC-01: EchoBox Unverified JWT Signature Verification (Critical Security Flaw in SUT)
- **File**: `var/repos/EchoBox/backend/lambda_function.py` (lines 120–146)
- **Vulnerability**: In the `authenticate_request()` function, when fallback ID Token authentication is executed, the backend splits the token (`token.split(".")[1]`), base64-decodes the payload claims, checks `exp` (expiry) and `iss` (issuer string), **but never verifies the cryptographic signature (`parts[2]`) against Cognito JWKS public keys**.
- **Impact**: An attacker can forge any JWT token with an arbitrary `sub` (e.g., impersonating any room owner or user) and a valid issuer URL, append any dummy signature, and gain full authorized access to owner actions (`close_room`, `reopen_room`, `delete_message`) and author actions (`delete_my_post`).
- **Remediation**: Must file high-severity defect `DEF-ECHO-006` in TraceTest AI defect catalog. Propose cryptographic JWKS verification using `python-jose` or AWS Cognito JWT verification guidelines with audience, token-use (`id` vs `access`), and key-rotation validation.

### SEC-02: Unsafe Git Subprocess Ingestion & Lack of SSRF Protections
- **File**: `backend/app/api/routers/projects.py` (lines 109–115)
- **Vulnerability**: `repo_url` and `branch` parameters passed to `POST /api/v1/projects/import-repo` are directly passed into `subprocess.run(["git", "clone", "--depth", "1", "-b", body.branch, body.repo_url, ...])`.
- **Impact**:
  1. **SSRF**: An attacker could provide `http://169.254.169.254/...` or internal subnet URLs.
  2. **Local Path Traversal / Git Arbitrary Code Execution**: Unvalidated branch names with argument flags (e.g. `--upload-pack`) could trigger arbitrary command execution.
- **Remediation**: Implement strict URL validation allowing only `https://github.com/` hosts, regex validation for repository owner/name (`^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`), and strict alphanumeric validation for branch/commit identifiers.

### SEC-03: Secret Scanning Absent on Ingested Code
- **Vulnerability**: The repository import pipeline does not scan for `.env` files, API keys, or embedded AWS secrets before passing code to AI analysis or LLM routers.
- **Remediation**: Integrate a regex-based secret redaction filter that strips PEM certificates, AWS keys (`AKIA...`), GitHub tokens, and `.env` files during AST and repository traversal.

---

## 4. Existing Architectural Weaknesses & Bugs

### ARCH-01: Hardcoded EchoBox Ingestion in Generic Router
- **Location**: `backend/app/api/routers/projects.py:121`
- **Issue**: `import_repository` endpoint calls `ingest_echobox_project()`. If a user connects `https://github.com/octocat/Hello-World`, TraceTest AI clones the repo but creates the `ECHO` project with EchoBox requirements.
- **Fix**: Refactor `repo_ingest.py` to decouple the generic repository analysis and dynamic requirement generator from the EchoBox reference catalog.

### ARCH-02: Missing Default Project Selection in Frontend Workspace
- **Location**: `frontend/src/hooks/useProjects.tsx` and `frontend/src/pages/DashboardPage.tsx`
- **Issue**: On a fresh session, `localStorage.getItem("tracetest.project")` is null. The frontend defaults to `null` or project 1 (`DF-PAY`). Because `DF-PAY` has 0 requirements, the dashboard displays the empty `DayforceOnboardingHub` instead of presenting the verified EchoBox project.
- **Fix**: If no project is stored in `localStorage`, default automatically to the designated default project (EchoBox `ECHO`).

### ARCH-03: Ambiguous Execution Environment Labeling
- **Location**: Frontend execution view and database models
- **Issue**: Previous views displayed "21/21 passed" without prominent, unmistakable differentiation between **In-Memory Harness** execution and **Live AWS Remote** execution, risking user confusion that the live cloud API is functioning.
- **Fix**: Enforce strict environment badges: `[In-Memory Harness]`, `[Static Analysis]`, `[Local Application]`, `[Browser E2E]`, `[Remote Test Environment]`, and `[Production Target]`.

---

## 5. Live AWS Integration Audit (HTTP 500)

- **Target URL**: `https://bnbpmiljw9.execute-api.ap-south-1.amazonaws.com`
- **Recorded Request ID**: `GYaZ0hH4BcwEMqw=`
- **Status Code**: `HTTP 500 Internal Server Error`
- **Body**: `{"error": "Internal server error"}`
- **Investigation Outcome**:
  - Live probe confirmed HTTP 500 response on `POST /` with `{"action": "discover_rooms"}`.
  - Review of `backend/lambda_function.py` line 77 indicates this payload is returned by the top-level `except Exception as e:` catch block.
  - Potential causes:
    1. DynamoDB table `"EchoBox"` does not exist in AWS region `ap-south-1`.
    2. Lambda execution role lacks IAM permissions (`dynamodb:Query`, `dynamodb:Scan`, `dynamodb:PutItem`).
    3. API Gateway HTTP API default integration failure or unhandled runtime crash.
  - **Blocker**: Local environment lacks AWS IAM credentials to query CloudWatch Log Group `/aws/lambda/EchoBox` or inspect API Gateway routes. Marked as **Blocked: Requires AWS CloudWatch read permissions**.

---

## 6. Test Coverage Gaps

1. **Multi-Project Isolation Tests**: No test currently verifies that importing Project B cannot access, overwrite, or leak test cases and requirements belonging to Project A.
2. **Repository URL Security Tests**: No unit tests testing malicious repository URLs (SSRF, argument injection, invalid schemes).
3. **JWT Signature Attack Tests**: No automated tests simulating forged JWTs against the authentication logic.

---

## 7. Prioritized Remediation Plan

| Priority | Task ID | Description | Target Component |
|---|---|---|---|
| **P0** | `REM-SEC-01` | Record `DEF-ECHO-006` for EchoBox JWT signature verification flaw; implement contract test suite. | `backend/app/db/`, `tests/` |
| **P0** | `REM-SEC-02` | Implement strict repository URL validation (SSRF and command injection defense). | `backend/app/services/repo_ingest.py` |
| **P1** | `REM-FE-01` | Set EchoBox (`ECHO`) as default workspace project in frontend state and overview dashboard. | `frontend/src/hooks/useProjects.tsx`, `DashboardPage.tsx` |
| **P1** | `REM-INGEST-01` | Generalize repository ingestion engine to parse any GitHub repo dynamically into independent projects. | `backend/app/services/repo_ingest.py`, `projects.py` |
| **P1** | `REM-FE-02` | Build "Connect GitHub Repository" UI modal supporting public URLs and branch/commit selection. | `frontend/src/pages/ProjectsPage.tsx`, `AppShell.tsx` |
| **P2** | `REM-TEST-01` | Add multi-project isolation test suite and import regression tests. | `backend/tests/test_projects.py` |
| **P2** | `REM-DOC-01` | Generate root `README.md` and complete `CLAUDE_ENGINEERING_HANDOFF.md`. | Repository root |
