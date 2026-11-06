# TraceTest AI — Supported Target Execution Matrix

This document defines the official matrix of target application architectures supported by TraceTest AI, specifying which target types support automated runtime execution in sandboxed environments versus those that are limited to static analysis and requirement extraction.

---

## 1. Target Architecture Matrix

| Target Type | Environment `kind` | Sandbox Isolation | Runtime Execution Support | Harness / Runtime Mechanism | Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Python Libraries / Packages** | `python_lib` | `bwrap+rlimits` (Linux) | **Full Execution** | In-process pytest runner executing pure Python functions and interfaces | Refuses execution if dependencies require missing C extensions |
| **Serverless AWS Lambda** | `real_code` | `bwrap+rlimits` (Linux) | **Full Execution** | Direct invocation of actual `lambda_function.py` entrypoint against local AWS mocks (`moto` DynamoDB, Cognito IDP) | Discrepancy comparison against secondary `simulation` harness |
| **Dayforce HCM Reference Apps** | `reference_hcm` | `bwrap+rlimits` / `netns` | **Full Execution** | Domain simulation models (v1.0 with 58 faults, v1.1 corrected build) with payroll calculations and policy checks | Fail-closed on missing rules |
| **HTTP REST Services** | `web` | `playwright:host_browser` / `bwrap` | **Probing & E2E** | Black-box HTTP requests and Playwright browser sessions dispatched against configured `base_url` | Skips live probing if target service is unreachable |
| **In-Memory Simulation Baseline** | `simulation` | `bwrap+rlimits` | **Baseline Execution** | In-memory reference mock used as a control baseline to detect discrepancies against real code | Used for regression and baseline delta tracking |
| **External Proprietary / Unsupported** | `static_only` | N/A | **Static Analysis Only** | Codebase AST parsing, README specification extraction, clause derivation, and secret scanning | **Fail-closed**: Any test execution attempt explicitly returns HTTP 400 `BadRequest: Static analysis only: no executable harness configured for target type 'static_only'` |

---

## 2. Invariant: Fail-Closed on Unsupported Targets

TraceTest AI never fakes execution results or simulates a passing test run for an unsupported target stack. 

When a repository outside the executable matrix (such as proprietary enterprise ERP systems, mainframe applications, or stacks requiring un-mocked cloud services) is ingested:
1. It is assigned an environment with `kind="static_only"`.
2. AST analysis extracts modules, endpoints, functions, and documentation clauses into traceable requirements.
3. If an operator attempts to execute a test suite against this environment, the API and execution engine immediately reject the request with:
   ```json
   {
     "error": "BadRequest",
     "message": "Static analysis only: no executable harness configured for target type 'static_only'"
   }
   ```
4. No synthetic execution record with passing metrics is ever generated.

---

## 3. Sandboxed Isolation Guarantees

All executable environments (`python_lib`, `real_code`, `reference_hcm`) execute strictly under **Bubblewrap containerization (`bwrap+rlimits`)**:
- **Filesystem Isolation**: Host directories (`/home`, `/var`, `/tmp`) are completely masked by in-memory `tmpfs` mounts. System libraries (`/usr`, `/lib`, `/lib64`, `/etc`) and the Python virtual environment (`/opt/venv`) are mounted strictly read-only.
- **Process Isolation**: Dedicated PID namespace (`--unshare-all`, `--die-with-parent`, `--new-session`), preventing child processes from signaling or inspecting host processes.
- **Network Isolation**: Outbound network connections are strictly unshared and blocked (`--unshare-net`), preventing credential or data exfiltration.
- **Resource Limits**: POSIX `rlimits` cap virtual memory (`RLIMIT_AS`), CPU time (`RLIMIT_CPU`), open file descriptors (`RLIMIT_NOFILE`), and output file size (`RLIMIT_FSIZE`).

