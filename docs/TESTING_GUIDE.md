# Testing Guide & Verification Workflows — TraceTest AI

## 1. Overview

TraceTest AI maintains rigorous test suites covering unit logic, integration workflows, AST security guardrails, sandbox isolation, and frontend rendering.

---

## 2. Running Test Suites

### 2.1 Backend Pytest Suite
Runs the 56 comprehensive unit and integration tests:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/ -v
```

**Test Modules**:
- `test_auth_permissions.py`: User roles, permissions, session management, and rate limiting.
- `test_guardrails.py`: Clause splitting, quote verification, ambiguity detection, and AST validator allowlists.
- `test_review_and_defects.py`: Test review lifecycle, defect triage transitions, and retest triggers.
- `test_sandbox.py`: Ephemeral directory creation, resource limit enforcement, and network blocking.
- `test_e2e_workflow.py`: End-to-end requirement analysis $\rightarrow$ test generation $\rightarrow$ approval $\rightarrow$ execution flow.
- `test_llm_router.py`: Slot rotation, failover mechanics, and circuit breaker tripping.
- `test_data_integrity.py`: Schema constraints, immutable snapshots, and cascade deletion rules.

### 2.2 Frontend Vitest & Testing Library
Runs the frontend test suite verifying React components and page navigation:
```bash
npm --prefix frontend test -- --run
```

### 2.3 Static Analysis & Typechecking
```bash
# Backend linting
PYTHONPATH=backend .venv/bin/ruff check backend

# Backend typechecking
cd backend && ../.venv/bin/mypy app/services/repo_ingest.py app/services/echobox_runner.py app/services/run_ai_eval.py
cd ..

# Frontend build & typecheck
npm --prefix frontend run build
```

---

## 3. EchoBox End-to-End Verification Pipeline

To execute the complete EchoBox verification pipeline (Tier A static, Tier B local sandbox, Tier C live AWS probe, Browser Playwright E2E, and defect seeding):
```bash
PYTHONPATH=backend .venv/bin/python backend/app/services/echobox_runner.py
```

### Expected Output Summary:
```
--- [Tier A] Static & Source Analysis ---
AST analysis: passed (13 actions verified)
TypeScript build: passed (4.61s)
--- [Tier B] Local Execution (Sandbox Pytest) ---
Tier B Execution finished: EX-000001 status=passed passed=21/21
--- [Tier C] Live AWS API Gateway Integration Probe ---
Tier C recorded: EX-ECHO-LIVE-001 status=error HTTP=500 in 574ms
--- [Browser E2E] Playwright Local Validation ---
Browser E2E finished: passed, screenshots: ['echobox-frontend-landing.png', 'echobox-join-validation.png']
--- [Defects] Seeding Genuine Discrepancies and Defect Records ---
Defects seeded: 5 new defects recorded.
```

---

## 4. Running Empirical AI Quality Evaluations

To benchmark Groq (`openai/gpt-oss-120b`) and Gemini (`gemini-2.5-flash`) on EchoBox scenarios:
```bash
PYTHONPATH=backend .venv/bin/python backend/app/services/run_ai_eval.py
```
Outputs clause coverage, ungrounded rate, schema pass rate, and slot latency metrics to `eval_runs` and `eval_results` tables.
