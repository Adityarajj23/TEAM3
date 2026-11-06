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
| **Repository Import Service** | **Verified** | `backend/app/services/repo_ingest/` modularized across 5 submodules. Supports dynamic AST parsing, generic requirements synthesis, and project isolation. |
| **EchoBox Ingestion into SQLite** | **Verified** | Project `ECHO` (id=5) exists in `var/tracetest.db`. Contains 8 modules, 2 environments, and full entity linkages. |
| **21 Requirements** | **Verified** | Exactly 21 rows in `requirements` table (`ECHO-REQ-001` through `ECHO-REQ-021`), mapped to `project_id=5`. |
| **62 Clauses** | **Verified** | Exactly 62 rows in `clauses` table linked across the 21 requirements. Each clause contains normalized text and analysis JSON. |
| **21 Acceptance Criteria** | **Verified** | Exactly 21 rows in `acceptance_criteria` table with source quotes and confidence scores. |
| **21 EchoBox Test Cases** | **Verified** | Exactly 21 automated test cases in `test_cases` table (`TC-ECHO-0001` through `TC-ECHO-0021`) with full Python/pytest scripts. |
| **In-Memory `echobox_harness`** | **Verified** | `echobox_harness/` directory contains `table.py` and `backend.py`. Conforms to `boto3` Table interface and dispatches all 13 EchoBox RPC actions. |
| **Sandbox Execution `EX-000001`** | **Verified** | Execution record `EX-000001` exists in `executions` table with status `passed`, 21 total, 21 passed, duration 1.92s. |
| **Live AWS Probe `EX-ECHO-LIVE-001`** | **Verified** | Probe recorded in `executions` with status `error`, duration 574ms. Live endpoint returns HTTP 500 (`{"error": "Internal server error"}`). |
| **5 Defects (`DEF-ECHO-001` – `005`)** | **Verified** | 5 defects present in `defects` table for `project_id=5` (`DEF-ECHO-001` through `DEF-ECHO-005`). |
| **Playwright Screenshots** | **Verified** | Authenticated high-fidelity laptop view screenshots (1440x900 canonical laptop view and 1280x800 standard laptop view) in `docs/screenshots/`. |
| **Groq / Gemini AI Evaluation** | **Verified** | Runs 3 (Groq, completed) and 4 (Gemini, degraded due to quota) are stored in `eval_runs` table in `var/tracetest.db`. |
| **33 Documentation Files** | **Verified** | All 33 markdown and schema documents present in `docs/` and verified via `scripts/verify_docs.py`. |
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

- **Target URL**: `https://<api-id>.execute-api.ap-south-1.amazonaws.com`
- **Recorded Request ID**: `[REQUEST-ID]`
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

## 6. Test Coverage & Gap Closures

1. **Multi-Project Isolation Tests**: Fully implemented in `test_multi_project_isolation.py` and `test_p2_reliability.py` (cross-project test/defect/execution ID tampering rejected with HTTP 404).
2. **Repository URL Security Tests**: Fully covered in `test_p0_security_remediations.py` and `test_multi_project_isolation.py` (SSRF IP validation, loopback blocks, command injection flag rejection).
3. **JWT Signature Attack Tests**: Implemented in `test_echobox_jwt_security.py` (10 tests) and `test_p1_fidelity_and_provenance.py` (real `lambda_function.py` under `moto` DynamoDB mock).

---

## 7. Prioritized Remediation Plan & Resolution Ledger

| Priority | Task ID | Description | Verified Implementation & Commit | Status |
|---|---|---|---|---|
| **P0** | `REM-SEC-01` | Record `DEF-ECHO-006` for EchoBox JWT signature flaw; test SUT fidelity. | Created `test_echobox_jwt_security.py` and `RealLambdaBackend` (`b2c27cf`). | **FIXED** |
| **P0** | `REM-SEC-02` | Implement strict repository URL validation (SSRF and command injection defense). | Built `url_validator.py` and `git_client.py` askpass (`b1676bb`, `5665d34`). | **FIXED** |
| **P0** | `REM-SEC-03` | Eliminate auto-admin session bypass; add Host/Origin and loopback binding. | Signed HMAC session cookies, Host middleware, 127.0.0.1 bind (`8780b43`). | **FIXED** |
| **P0** | `REM-SEC-04` | Untrusted repo host code execution sandbox containment. | Static AST parsing, fail-closed isolation, `RLIMIT_NPROC=64` (`0a48b30`, `cca51d0`). | **FIXED** |
| **P1** | `REM-FE-01` | Set EchoBox (`ECHO`) as default workspace project in frontend. | `useProjects.tsx` and `DashboardPage.tsx` default to `ECHO` (`da814ce`). | **FIXED** |
| **P1** | `REM-INGEST-01` | Modularize and generalize repository ingestion into independent submodules. | Modularized into `app/services/repo_ingest/` (`5665d34`). | **FIXED** |
| **P1** | `REM-FE-02` | Build "Connect GitHub Repository" modal supporting URL and branch selection. | Verified in `ProjectsPage.tsx` and `AppShell.tsx` (`da814ce`). | **FIXED** |
| **P1** | `REM-DATA-01` | Add defect evidence type and requirement provenance. | Alembic migration `0002` + provenance fields (`b2c27cf`). | **FIXED** |
| **P2** | `REM-REL-01` | SQLite WAL concurrency discipline and task reconciliation. | `busy_timeout=10000`, 30 concurrent writes test, recovery hook (`5665d34`). | **FIXED** |
| **P2** | `REM-DOC-01` | Complete 33 documentation files, demo script, slides, and evaluation report. | Complete suite verified via `scripts/verify_docs.py` (`8bcd14f`). | **FIXED** |
