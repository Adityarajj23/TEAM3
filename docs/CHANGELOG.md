# Changelog & Release History — TraceTest AI

All notable changes to the TraceTest AI platform are documented in this file.

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
  - **Tier C**: Live AWS API Gateway integration probe capturing HTTP 500 upstream server error with request ID `GYaZ0hH4BcwEMqw=`.
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
