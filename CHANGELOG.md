# Changelog

All notable changes to **TraceTest AI** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-05

### Added
- **Multi-Credential AI Pooling (`SlotPool`)**:
  - Full support for 3 Groq API keys (`GROQ_API_KEY`, `GROQ_API_KEY2`, `GROQ_API_KEY3`) and 3 Gemini API keys (`GEMINI_API_KEY`, `GEMINI_API_KEY2`, `GEMINI_API_KEY3`).
  - Automatic round-robin rotation, 60-second rate-limit cooldown on HTTP 429, and permanent invalidation on HTTP 401/403.
  - Zero-leakage provider telemetry via `/api/config` and `/api/health`.
- **Model Compatibility & Truncation Protection**:
  - Upgraded Google Gemini default model to `gemini-2.5-flash` with automatic fallback.
  - Configured `max_tokens: 4096` on Groq requests, resolving `json_validate_failed` schema truncation errors.
- **Enterprise UI & Responsive Floor**:
  - Dynamic viewport units (`min-h-[100dvh]`) across all layouts, eliminating mobile and virtual keyboard layout shifts.
  - Viewport stability via `overflow-x: clip` on `html` and `body`.
  - Zero-delay `:focus-visible` ring styling for WCAG AA keyboard accessibility.
  - Complete `@media (prefers-reduced-motion: reduce)` motion fallbacks.
  - Automated Playwright visual testing across 25 routes at 1440px and 1024px with zero horizontal scroll overflow.
- **Comprehensive Documentation Suite**:
  - `docs/ARCHITECTURE.md`: Complete C4-style architectural specifications and data flow diagrams.
  - `docs/DECISIONS.md`: 10 Architecture Decision Records (ADRs 001-010).
  - `docs/API.md`: Full REST API reference guide.
  - `docs/DATABASE.md`: Relational schema across 36 tables, WAL mode, foreign key constraints, and seed catalog.
  - `docs/SECURITY.md`: Enterprise security posture, Argon2id, CSRF, RBAC, project isolation, and sandbox boundaries.
  - `docs/AI_PIPELINE.md`: LangGraph state graphs, persistent checkpoints, and deterministic guardrails.
  - `docs/EXECUTION_ENGINE.md`: AST allowlist, POSIX resource rlimits, Linux network namespaces, and artifact digests.
  - `docs/REFERENCE_HCM.md`: Dual-build SUT specifications (HCM v1.0 deliberate faults vs v1.1 fixes).
  - `docs/TESTING.md`: Automated test matrix across backend, frontend, and visual regression suites.
  - `docs/DEPLOYMENT.md`: Production prerequisites, systemd unit files, NGINX TLS reverse proxy, and backup procedures.
  - `docs/USER_GUIDE.md`: Operational walkthrough for test authors, leads, reviewers, and compliance auditors.
  - `docs/PROGRESS.md`: Empirical verification audit and milestone tracking.

### Fixed
- **Reference HCM Seed Automation Defects**:
  - Corrected `leav.` typo in `TC-LVE-0026` (`leave.accrue_leave`).
  - Corrected `payrol.` typo in `TC-PAY-0016` (`payroll.calculate_gross_pay`).
  - Verified that on HCM v1.1, both test cases now pass cleanly (96 passing tests total).
- **Legitimate Engine Boundary Clarification**:
  - Documented that exactly 4 tests fail on HCM v1.1 due to unsupported group differential rates (6%/12% and 7%/15%), confirming that defects remain open without manufactured results.
- **Project Isolation Query Scoping**:
  - Fixed closed defect query tests in `test_review_and_defects.py` to scope queries to reviewer's authorized projects, resolving HTTP 404 access conflicts.
- **Test Harness Environment Isolation**:
  - Updated `backend/tests/conftest.py` to blank out all multi-key environment variable aliases during unit test runs, preventing unintentional live network calls during fixture runs.

### Security
- Hardened `.gitignore` to strictly exclude all credential files (`.env*` except `.env.example`), local SQLite databases (`*.db*`), and runtime execution artifacts.
- Verified zero credential or key-substring leakage in Git commit history, API responses, and client bundles.
