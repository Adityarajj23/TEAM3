# System Boundaries & Known Limitations — TraceTest AI

## 1. Overview

In accordance with enterprise transparency and rigorous verification standards, this document details the architectural boundaries, sandbox constraints, and operational limitations of TraceTest AI.

---

## 2. Target Application Cloud Limitations (EchoBox AWS Endpoint)

### Live AWS API Gateway Blocked State (`DEF-ECHO-005`)
- **Observed Behavior**: Live probes targeting `https://bnbpmiljw9.execute-api.ap-south-1.amazonaws.com` return `HTTP 500 Internal Server Error`.
- **Root Cause**: The upstream AWS Lambda function or DynamoDB table (`EchoBox`) in AWS region `ap-south-1` is currently unseeded or misconfigured.
- **Handling**: TraceTest AI records this state as `blocked` in Tier C execution reports rather than faking a 200 OK response. Full local validation is maintained via the in-memory test-safe harness (`echobox_harness`).

---

## 3. Subprocess Sandbox Constraints

1. **Network Namespace Dependency (`unshare -rn`)**:
   - The private network namespace feature requires Linux kernel support for unprivileged user namespaces (`kernel.unprivileged_userns_clone = 1`).
   - On hosts where `unshare` is restricted by security policies, the sandbox relies on the Python guard `conftest.py` socket blocker.
2. **Virtual Memory Bounds (`RLIMIT_AS`)**:
   - Pytest scripts are restricted to 512MB virtual address space.
   - For Playwright browser runs, `RLIMIT_AS` is disabled because modern Chromium processes reserve large virtual address spaces on startup.
3. **AST Allowlist Restriction**:
   - Third-party packages that require C-extensions or direct socket manipulation cannot be executed inside the Pytest sandbox unless wrapped in an approved domain harness.

---

## 4. AI Provider Quotas & Rate Limits

1. **Free Tier Quota Limits (Google Gemini)**:
   - Google Gemini Free Tier limits accounts to 20 requests per day for `gemini-2.5-flash`.
   - High-volume evaluation suites may trigger `429 RESOURCE_EXHAUSTED`.
   - TraceTest AI automatically falls back to Groq (`openai/gpt-oss-120b`) and records degraded status for exhausted slots.
2. **Deterministic Output Repair Passes**:
   - Self-repair passes are limited to a maximum of 2 attempts. If an LLM repeatedly fails to produce valid JSON conforming to the Pydantic schema, the request raises `StructuredOutputError`.

---

## 5. Database Scale Boundaries

- **SQLite WAL Concurrency**: SQLite supports virtually unlimited concurrent readers and single-writer concurrency with immediate consistency.
- **Recommended Data Scale**: Optimal for workspaces up to 500,000 test cases, 50,000 executions, and 20GB database size. For planetary-scale distributed deployments exceeding 10M executions, migration to PostgreSQL can be configured via SQLAlchemy connection strings.

