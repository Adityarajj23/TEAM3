# Changelog & Release History — TraceTest AI

All notable changes to the TraceTest AI platform are documented in this file.

---

## [1.3.0] — 2026-11-06 (Production Hardening & Verification Release)

### Security (P0)
- **Eliminated Dummy Session Bypass**: Replaced insecure dummy admin session fallback with cryptographically signed HMAC operator session cookies (`SameSite=Strict`, `HttpOnly=True`). Added Host and Origin header validation middleware and enforced strict `127.0.0.1` loopback binding (`8780b43`).
- **Prohibited Untrusted Host Execution**: Eliminated host `npm run build` and `npx vite preview` on untrusted target repositories, replacing them with safe static AST/manifest analysis (`0a48b30`).
- **Hardened Git Ingestion**: Implemented `run_hardened_git` in `git_client.py` using a `0700` transient `GIT_ASKPASS` script, restricted git flags (`core.hooksPath=/dev/null`, `protocol.file.allow=never`), and enforced 250MB / 10,000 files limits (`b1676bb`).
- **Fail-Closed Sandbox**: Implemented `detect_isolation_level()` and enforced `require_network_isolation=True`. Added `RLIMIT_NPROC=64` to prevent fork bombs and hardened AST allowlist against dunder attribute traversal (`cca51d0`).

### SUT Fidelity & Provenance (P1)
- **Real SUT Execution under Moto**: Created `RealLambdaBackend` in `echobox_harness/backend.py` executing the actual `lambda_function.py` against DynamoDB single table under `moto.mock_aws()`, faithfully uncovering `DEF-ECHO-006` (unverified JWT signatures) (`b2c27cf`).
- **Data Provenance & Classification**: Added `evidence_type` and `source_commit_sha` to defects; added `origin`, `source_commit_sha`, and `confidence` to requirements (inferred requirements default to `needs_confirmation`) via Alembic migration `0002_security_and_provenance.py` (`b2c27cf`).
- **Pre-Flight Prompt Secret Redaction**: Added regex scrubber in `app/llm/router.py` stripping AWS keys, SSH keys, GitHub tokens, and Groq/Gemini API keys before model submission (`b2c27cf`).

### Reliability & Architecture (P2)
- **Modularized Repository Ingestion**: Decomposed 2,070-line monolithic `repo_ingest.py` into 5 cohesive submodules in `app/services/repo_ingest/` (`url_validator.py`, `secret_scanner.py`, `ast_analyzer.py`, `echobox_derivation.py`, `generic_derivation.py`) (`5665d34`).
- **SQLite WAL Concurrency**: Verified SQLite WAL concurrency with 30 concurrent writes across 8 threads and configured `busy_timeout=10000` (`5665d34`).
- **Background Task Reconciliation**: Implemented startup recovery hook (`recover_interrupted`) marking orphaned running tasks as `interrupted` upon server restart (`5665d34`).
- **Cross-Project Isolation**: Enforced strict project boundary verification across test cases, executions, and requirements, rejecting cross-project ID tampering with HTTP 404 (`5665d34`).

### UI & Polish
- **6-Stage Project Journey Header**: Added visual, step-by-step project journey header (Connect, Analyze, Requirements, Test Generation, Execute, Defects) in `DashboardPage.tsx` (`8bcd14f`).
- **Environment & Isolation Badges**: Surfaced sandbox isolation level and execution environment badges across `AppShell.tsx`, `/config` API, and execution detail views (`8bcd14f`).
- **Defect Evidence Metadata**: Displayed defect evidence classification tags and source commit SHAs in defect views (`8bcd14f`).

### Documentation & Challenge Deliverables
- **Challenge Artifacts**: Added `docs/demo-script.md` (10-min presenter script), `docs/slides-outline.md` (5-slide presentation deck), and `docs/eval-report.md` (reproducible benchmark report).
- **Automated Verification Suite**: Enhanced `scripts/verify_docs.py` to validate all 36 SQLAlchemy tables, security invariants, internal links, and zero secret leakage.
- **Visual Assets**: Captured 60 authenticated Playwright screenshots across 6 responsive viewports and generated clean axe-core accessibility audit report (`docs/a11y-report.json`).

---

## [1.2.0] — 2026-11-06 (EchoBox Production-Grade QA Case Study Release)

### Added
- **EchoBox Case Study (`ECHO`)**:
  - Full ingestion of [sohan10012/EchoBox](https://github.com/sohan10012/EchoBox.git).
  - Automated extraction of 21 source-grounded requirements across 8 modules (`ECHO-ROOMS`, `ECHO-DISCOVERY`, `ECHO-CHAT`, `ECHO-OWNER`, `ECHO-IDENTITY`, `ECHO-EXPIRY`, `ECHO-SECURITY`, `ECHO-FRONTEND`).
  - Generated 62 atomic clauses with exact source file and line attribution.
  - Generated and validated 21 executable Pytest and contract test cases (`TC-ECHO-0001` through `TC-ECHO-0021`).
- **Multi-Tiered Verification Pipeline (`app/services/echobox_runner.py`)**:
  - **Tier A**: Static AST action matrix extraction (13 actions) and TypeScript compilation check (clean build in 4.61s).
  - **Tier B**: Local test-safe in-memory execution harness (`echobox_harness`) running in POSIX sandbox (21/21 passed in 1.92s).
  - **Tier C**: Live AWS API Gateway integration probe capturing HTTP 500 upstream server error with request ID `[REQUEST-ID]`.
  - **Browser E2E**: Playwright headless browser automation against local Vite preview server, capturing full-page UI screenshots.
- **Defect Tracking Ledger**:
  - Seeded 5 verified genuine defects (`DEF-ECHO-001` through `DEF-ECHO-005`):
    - Description limit discrepancy (500 doc vs 1000 code).
    - Silent input slicing on room name and description.
    - Invalid visibility fallback to public space.
    - Discovery loop N+1 query amplification.
    - Live AWS API Gateway HTTP 500 error.
- **Repository Ingestion API (`POST /api/v1/projects/import-repo`)**:
  - Shallow git clone of public repositories without requiring GitHub token.
  - Directory classification and Python AST action parser.
- **AI Evaluation Benchmark Suite (`backend/app/services/run_ai_eval.py`)**:
  - Empirical evaluation comparing Groq (`openai/gpt-oss-120b`) and Gemini (`gemini-2.5-flash`).
  - Recorded 100% clause coverage and 0% duplicates on Groq.
  - Demonstrated slot pool failover and circuit breaker tripping on Gemini 429 quota exhaustion.

### Changed
- Extended AST allowlist in `app/guardrails/ast_validator.py` to support `echobox_harness` package.
- Enhanced execution sandbox (`app/execution/sandbox.py`) to automatically mount `echobox_harness` alongside `reference_hcm`.
- Updated `app/services/executions.py` to allow automated Pytest contract runs on web environments.
- Updated `docs/openapi.json` with repository import endpoint schemas.

---

## [1.1.0] — 2026-11-05 (Dayforce HCM Enterprise Edition)

### Added
- Dayforce HCM Quality Engineering Workspace with 4 core projects:
  - `DF-PAY`: Dayforce Payroll Verification.
  - `DF-WFM`: Dayforce Workforce Management.
  - `DF-LVE`: Dayforce Absence & Leave.
  - `DF-BEN`: Dayforce Benefits & Eligibility.
- Reference HCM Golden System with version 1.0 (baseline) and version 1.1 (candidate fix).
- Multi-slot LLM credential rotation supporting 3 keys each for Groq and Gemini.
- Single-operator UI mode removing consumer login screens.

### Fixed
- Fixed SQLite WAL connection pragmas to prevent database locking during concurrent test runs.
- Fixed AST validator to block dangerous builtins (`eval`, `exec`, `open`).

---

## [1.0.0] — 2026-11-04 (Initial Platform Release)

### Added
- Core architecture: FastAPI backend and React/Vite frontend.
- Deterministic clause segmentation and quote verification.
- Defense-in-depth POSIX execution sandbox.
- Bidirectional traceability matrix and mathematical coverage calculation.

