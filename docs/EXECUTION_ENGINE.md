# Execution Engine & Defense-in-Depth Sandbox — TraceTest AI

## 1. Overview

The TraceTest AI Execution Engine provides an isolated, deterministic execution harness for automated test suites. Operating across multiple verification tiers, the engine runs tests against local domain logic, test-safe in-memory harnesses, and live cloud endpoints, capturing JUnit XML reports, console logs, and visual browser artifacts.

---

## 2. Multi-Tiered Verification Matrix

| Tier | Scope | Target Environment | Execution Runner | EchoBox Validation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Tier A** | Static Analysis & AST Inspection | Code repository source tree | Python AST & TypeScript Compiler | **Passed**: 13 RPC actions verified, 0 forbidden builtins, TS build in 4.61s. |
| **Tier B** | Local Test-Safe Application Execution | In-memory DynamoDB & Lambda harness (`echobox_harness`) | Sandbox Pytest (POSIX isolated) | **Passed**: 21 / 21 test cases passed (100% pass rate in 1.9s). |
| **Tier C** | Live Cloud Integration Probe | Live AWS HTTP API Gateway (`ap-south-1`) | Live HTTP / REST probe | **Blocked**: Accurately captured HTTP 500 error (unseeded DynamoDB). |
| **Browser E2E** | Local Frontend User Experience | Local Vite preview server (`http://localhost:5174`) | Playwright Chromium (headless) | **Passed**: Verified Join Room navigation & captured screenshots. |

---

## 3. Defense-in-Depth Sandbox Layers (`sandbox.py`)

Every automated Pytest execution is guarded by six defensive isolation boundaries:

1. **AST Pre-Check**: Test scripts must pass AST allowlist validation before execution begins.
2. **Fresh Ephemeral Directory**: Each execution generates a temporary directory (`/tmp/tt-sandbox-XXXXXX`) containing only the test files, clean public domain packages (`echobox_harness`, `reference_hcm`), and guard conftest.
3. **Hermetic Environment**:
   - The subprocess executes with an empty environment (`env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(work), "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"}`).
   - Python runs in isolated mode: `python3 -I -B -m pytest -q -p no:cacheprovider`.
4. **POSIX Resource Limits (`setrlimit`)**:
   - `RLIMIT_CPU`: Maximum 60 CPU seconds.
   - `RLIMIT_FSIZE`: Maximum 50MB file output.
   - `RLIMIT_CORE`: 0 (core dumps disabled).
   - `RLIMIT_AS`: Virtual address space capped at 512MB (skipped for Playwright browser runs).
   - `RLIMIT_NOFILE`: Capped at 256 open file descriptors.
5. **Network Isolation**:
   - Guard `conftest.py` monkeypatches `socket.socket`, `socket.create_connection`, and `socket.getaddrinfo` to raise `RuntimeError("Network access is disabled in the TraceTest sandbox")`.
   - On Linux systems supporting unprivileged user namespaces, the child process is executed under `unshare -rn` (isolated network namespace with loopback only).
6. **Hard Process Termination**:
   - Enforced wall-clock timeout kills the entire process group if a test hangs.

---

## 4. Playwright Browser Automation

For Web and UI environments:
- Playwright controls headless Chromium (`/usr/bin/chromium`).
- Launches with flags: `--no-sandbox`, `--disable-dev-shm-usage`.
- Collects browser console logs and attaches them to execution results.
- Captures full-page screenshots on completion or failure.

---

## 5. Artifacts & Result Persistence

Upon execution completion:
- Standard output and error streams are truncated to safe bounds and logged.
- JUnit XML reports are parsed to extract per-test durations, failure messages, and stack traces.
- Artifacts are stored under `var/artifacts/executions/EX-XXXXXX/`:
  - `pytest-output.log`: Full stdout/stderr stream.
  - `junit.xml`: Machine-readable test outcome report.
  - `screenshots/`: PNG screenshots from browser runs.
