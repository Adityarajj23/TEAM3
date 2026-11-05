# User Guide & Operational Walkthrough — TraceTest AI

## 1. Introduction

TraceTest AI provides a single-operator enterprise workspace for quality engineering, requirement verification, automated test generation, and defect resolution.

---

## 2. Navigating the Workspace

The sidebar organizes the verification lifecycle into logical stages:

1. **Workspace Switcher**: Select between Dayforce HCM projects (`DF-PAY`, `DF-WFM`, `DF-LVE`, `DF-BEN`) and imported repositories (`ECHO`).
2. **Overview**: View executive metrics: requirement count, approved tests, open defects, and mathematical coverage percentage.
3. **Requirements**: Browse versioned specifications, view clause breakdowns, check ambiguity flags, and trigger AI requirement analysis.
4. **Test Cases**: Inspect executable test scripts, review validation status, and filter tests by category (positive, boundary, authorization, security, expiration).
5. **Approval Workspace**: Human-in-the-loop review station to approve, edit, or reject newly generated tests.
6. **Suites**: Organize test cases into functional modules (e.g. `ECHO-ROOMS`, `ECHO-CHAT`).
7. **Executions**: Run test suites against target environments, view real-time stdout/stderr logs, and inspect JUnit XML reports.
8. **Defects**: Review logged defects, inspect AI root-cause analysis, and trigger automated retests against candidate fix builds.
9. **Traceability**: Explore the interactive requirement-to-defect matrix.
10. **Settings**: Monitor AI provider slot pools, check circuit breaker states, and manage API credentials.

---

## 3. Step-by-Step Walkthrough: Verifying EchoBox

### Step 1: Ingesting the Codebase
1. Open **Settings** $\rightarrow$ **Repository Ingestion** (or dispatch `POST /api/v1/projects/import-repo`).
2. Enter repository URL: `https://github.com/sohan10012/EchoBox.git`.
3. The platform performs shallow clone, scans the AST for 13 RPC actions, decomposes the architecture into 8 modules, and creates the `ECHO` project.

### Step 2: Inspecting Requirements & Clauses
1. Navigate to **Requirements** and select `ECHO-REQ-001` (Room Creation).
2. Note the provenance badge: `Directly observed in source` pointing to `backend/lambda_function.py:153-235`.
3. Inspect segmented clauses:
   - `ECHO-REQ-001.C1`: 8-character hexadecimal room ID.
   - `ECHO-REQ-001.C2`: 24-hour expiration epoch calculation.
   - `ECHO-REQ-001.C3`: Metadata persistence under `ROOM#{id}`.

### Step 3: Reviewing Test Cases
1. Open the **Approval Workspace**.
2. Inspect `TC-ECHO-0003` (Message 2000-char boundary).
3. Verify that the verbatim quote `if len(clean_msg) > 2000:` matches the source clause text.
4. Click **Approve** to unlock the test for execution.

### Step 4: Executing Tests in Sandbox
1. Navigate to **Executions** and click **Run Suite**.
2. Select target environment: `EchoBox Local Test Harness`.
3. The sandbox executes all 21 test cases in an isolated POSIX container with network blocking.
4. Observe test progress and view the final result: **21 / 21 Passed (100% in 1.9s)**.

### Step 5: Triaging Defects
1. Navigate to **Defects**.
2. Inspect `DEF-ECHO-001` (Description length mismatch: 500 chars vs 1000 chars).
3. Review reproduction steps, code snippet (`clean_desc = room_desc[:1000]`), and AI root-cause analysis.
4. Transition status to `in_progress` or export to GitHub Issues.
