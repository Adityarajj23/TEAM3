# Architecture Decision Records (ADRs)

This document records the architectural and engineering decisions made during the development of TraceTest AI, including the context, considered alternatives, rationale, and consequences of each choice.

---

## ADR-001: SQLite as the Sole Application and Workflow Database

### Context
Enterprise test management and QA platforms typically store requirements, test suites, execution artifacts, defect records, and audit logs. The system must support local laptop development, CI/CD pipeline execution, and self-hosted on-premises deployments without heavyweight operational overhead.

### Decision
Use SQLite in Write-Ahead Logging (WAL) mode as the sole persistence technology across the application. Partition data into two dedicated SQLite databases:
1. `var/tracetest.db`: Business entities, test cases, executions, defects, user accounts, sessions, and audit trails.
2. `var/workflow_checkpoints.db`: LangGraph execution state, thread checkpoints, and resume state, managed directly by `langgraph-checkpoint-sqlite`.

### Consequences & Trade-offs
- **Pros**: Zero infrastructure dependencies (no Postgres, Redis, or MongoDB required); instantaneous initialization; embedded ACID transactions; online non-blocking hot backups (`sqlite3.backup()`).
- **Cons**: Write concurrency is limited to a single active writer at any time. Addressed by designing short, atomic transactions and offloading long-running jobs to in-process workers that commit immediately.

---

## ADR-002: Alembic Migrations with SQLite Batch Mode

### Context
Relational database schemas evolve over time as new features are added. SQLite has historically had limited support for `ALTER TABLE` operations (e.g. dropping columns, altering constraints).

### Decision
Manage database schema migrations exclusively through Alembic using SQLAlchemy models as the single source of truth. Enforce `render_as_batch=True` across all migration files to utilize SQLite table recreation batch operations.

### Consequences
- Full backward and forward schema traceability.
- Idempotent startup migration (`alembic upgrade head`) executes reliably on application launch.
- Foreign keys and check constraints are preserved across column modifications.

---

## ADR-003: Deterministic Guardrails First, LLM Interpretation Second

### Context
Generative AI models are stochastic, prone to hallucinations, formatting variances, and subtle injection exploits. An enterprise QA platform cannot trust model output to guarantee safety, approval status, or test validity.

### Decision
Enforce a strict architectural boundary:
1. **Deterministic Guardrails**: Clause segmentation, stable identifier generation, quote verification, coverage analysis, deduplication, AST security validation, and role-based permissions are implemented entirely in deterministic Python code.
2. **LLM Role**: The LLM is restricted to semantic reasoning, test step drafting, edge-case hypothesis generation, and failure explanation.
3. **No Code Alteration of Grounding**: Generated test cases or criteria that fail quote verification or reference nonexistent clauses are rejected and flagged as ungrounded; they are never silently synthesized or repaired by code.

### Consequences
- Mathematical auditability of requirements-to-test traceability.
- Complete resistance to prompt injection escaping into executable actions.
- Model upgrades or provider shifts cannot compromise security or approval policies.

---

## ADR-004: Multi-Credential Key Pools and Provider Failover Hierarchy

### Context
Cloud LLM providers impose strict per-minute token and request rate limits. Single-key setups fail unpredictably under burst load or team testing sessions.

### Decision
Implement a multi-credential rotation and failover architecture:
- Support up to three credentials per provider (`Slot 1`, `Slot 2`, `Slot 3`) via environment variables (`GROQ_API_KEY`, `GROQ_API_KEY2`, `GROQ_API_KEY3` / `GEMINI_API_KEY`, etc.).
- Maintain an in-memory `SlotPool` for each provider tracking state (`healthy`, `rate_limited`, `invalid`).
- On HTTP 429 or quota depletion, immediately rotate to the next healthy slot in the pool.
- On HTTP 401/403 (invalid key), permanently disable the bad slot without failing the whole request.
- Primary provider is Groq (`openai/gpt-oss-120b`). Secondary provider is Gemini (`gemini-2.5-flash`). Optional local provider is Ollama (`llama3.1`).
- Fall back to secondary provider only when all primary slots are exhausted.

### Consequences
- Zero downtime during burst test generation or evaluation runs.
- Full compliance with provider rate limits and `Retry-After` response headers.
- Safe logging: credential secrets are strictly masked and never logged or exposed in API payloads.

---

## ADR-005: Process-Level Sandbox with AST Allowlist and Linux Namespaces

### Context
Approved automated tests are executed in Python against the System Under Test. Running untrusted or AI-generated Python code directly on a host server poses remote code execution risks.

### Decision
Construct a multi-layered process-level execution sandbox:
1. **Pre-execution AST inspection**: Scripts must pass an Abstract Syntax Tree validator allowing only approved modules (`pytest`, `reference_hcm.*`, `math`, `decimal`, `datetime`). Disallowed nodes (`os`, `sys`, `subprocess`, `socket`, `open`, `eval`, `exec`, `while`) cause immediate pre-execution rejection.
2. **Resource Limits**: POSIX `resource.setrlimit` limits memory (512 MB), CPU time, open files (256), and file size (50 MB).
3. **Network Isolation**: When available on Linux, runs are spawned under `unshare -rn` (isolated network namespace). All environments bundle a security `conftest.py` that nullifies network sockets.
4. **Hard Timeout**: Subprocess process groups are forcefully terminated on timeout expiration.

### Consequences
- Secure and deterministic execution on developer workstations and CI runners without requiring Docker daemon permissions.
- Documented limitation: This is a process sandbox, not a virtualization container; enterprise deployments with untrusted multi-tenant code authors should place the API host in an isolated VM.

---

## ADR-006: LangGraph Workflows with Interrupt-Before Human Review

### Context
Test generation and defect triage require human authorization. Workflows must pause cleanly for human intervention and resume without state loss, even across server restarts.

### Decision
Model workflows as LangGraph state graphs with `SqliteSaver` checkpointers:
- In requirement generation, the graph executes up to `gap_checker` and interrupts before `human_review`.
- In failure analysis, the graph executes up to `defect_recommendation` and interrupts before `human_approval`.
- Checkpoints are saved to `workflow_checkpoints.db` indexed by thread ID.
- When an authorized user submits an approval or review decision via the REST API, the workflow thread resumes and completes.

### Consequences
- Human-in-the-loop governance is baked into the engine architecture.
- Workflows survive server restarts and application updates.

---

## ADR-007: Verification-Grounded Defect Lifecycle

### Context
Bug tracking systems often allow defects to be marked "verified" or "closed" without proof that a test actually passed on a corrected build, leading to regression escapes.

### Decision
Enforce state machine constraints directly in the defect service:
- A defect can only transition to `verified` if a linked test execution on a fix candidate build (e.g. Reference HCM 1.1) records a genuine `passed` outcome for that specific test script.
- Transitioning without a passing execution result returns HTTP 409 Conflict with an actionable message.

### Consequences
- Eliminates "paper verification" where defects are closed administratively without empirical proof.
- Full traceability linking requirements → tests → failures → defects → retest execution results.

---

## ADR-008: Server-Side Cryptographic Sessions and CSRF Headers

### Context
Single-Page Applications (SPAs) communicating with a REST API need secure authentication resistant to XSS and CSRF attacks.

### Decision
- Use server-side session tokens stored in `HttpOnly`, `SameSite=Lax` cookies.
- Only the SHA-256 hash of the session token is persisted in the database.
- Require an `X-CSRF-Token` header on all mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- Passwords hashed with Argon2id using `argon2-cffi`.

### Consequences
- Tokens cannot be stolen via JavaScript XSS.
- Cross-origin requests cannot forge state mutations.
- Immediate revocation on logout or admin session invalidation.

---

## ADR-009: In-Process Asynchronous Worker Pool with SSE Progress

### Context
Operations such as requirement generation, test suite execution, and AI evaluations take seconds to minutes. Background execution must not block the HTTP request thread.

### Decision
Use a lightweight in-process thread pool worker (`concurrent.futures.ThreadPoolExecutor`) tied to database-backed run records (`runs` and `run_steps` tables):
- Progress is updated in SQLite as steps complete.
- Clients subscribe to live progress via Server-Sent Events (`GET /api/v1/runs/{id}/events`).
- Frontend automatically falls back to polling `GET /api/v1/runs/{id}` if SSE is interrupted.
- Orphaned runs from ungraceful server shutdowns are detected on startup and marked `failed`.

### Consequences
- Zero external message broker dependencies (no Redis, RabbitMQ, or Celery).
- Real-time user feedback with smooth progress bars and live step logs.

---

## ADR-010: Reference HCM Dual-Engine System Under Test

### Context
To rigorously verify a QA automation platform, realistic, reproducible software faults and fixes must exist in a controlled system under test.

### Decision
Package a dual-build reference Human Capital Management system (`reference_hcm`):
- `v1.0`: Contains 8 deliberate, documented domain faults (overtime off-by-one, rounding mode mismatch, differential rate swap, cutoff boundary error, break threshold error, leave cap bypass, contractor eligibility defect, approval limit strictness).
- `v1.1`: Fix candidate build with all 8 deliberate faults resolved.
- Unsupported engine behavior: Group-specific differential overrides (security officers 6%/12%, clinic staff 7%/15%) remain unsupported in both builds, accurately modeling real-world engine limitations.

### Consequences
- Empirically validates that TraceTest AI detects real faults in v1.0 and verifies real fixes in v1.1.
- Provides consistent ground-truth for regression testing and CI verification.

---

## ADR-011: Strict Loopback Binding, Host/Origin Validation, and Elimination of Single-Operator Bypass

### Context
Prior implementations permitted unauthenticated requests in single-operator mode to synthesize a temporary `UserSession(id=0)` with all administrative roles, bypassing CSRF verification. Furthermore, documentation previously advised binding to `0.0.0.0`, which risked exposing an unauthenticated administrative API to the local network or internet.

### Decision
1. Default bind host is strictly `127.0.0.1`. If `TRACETEST_SINGLE_OPERATOR` is true, binding to non-loopback hosts (`0.0.0.0` or external IPs) is explicitly rejected at startup.
2. In single-operator mode, the first page load (`GET /api/v1/auth/me`) mints a real signed local session cookie in SQLite with `SameSite=Strict` and `HttpOnly=True`, along with a matching `SameSite=Strict` CSRF cookie.
3. Completely remove synthetic `id=0` sessions. All state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require a valid session cookie and matching `X-CSRF-Token`.
4. Validate `Host` header against `localhost`, `127.0.0.1`, `[::1]`, and configured allowlists to defeat DNS rebinding.
5. Validate `Origin` header on state-changing requests to reject untrusted cross-origin requests with HTTP 403.
6. Refuse to start in production mode if the default `secret_key` (`change-me-in-env`) is detected; in development, auto-generate a cryptographically secure random token persisted to `data_dir / ".secret_key"` (mode 0600).

### Consequences
- Eliminates cross-site request forgery and DNS rebinding attack vectors against the local developer instance.
- Fully prevents LAN/WAN exposure of single-operator administrative operations.
- Guarantees complete audit traceability: all operations are tied to a persistent session record in the database.

---

## ADR-012: Prohibition of Untrusted Repository Code Execution on the Host

### Context
Target repositories imported into TraceTest AI are fundamentally untrusted external inputs. In earlier validation scripts (`echobox_runner.py`), `npm run build` and `npx vite preview` were invoked directly on the host system via `subprocess`. A malicious repository containing arbitrary shell commands in lifecycle hooks (`preinstall`, `postinstall`, `build`) would achieve remote code execution on the host machine.

### Decision
1. Strictly treat all target repositories as untrusted inputs. Zero script execution (e.g. `npm run`, `npm install`, `node`, `make`, `python`) is permitted directly on the host environment.
2. In Tier A static verification, replace shell compilation checks with purely static manifest and AST analysis: parse `package.json`, inspect script definitions, count dependencies, and validate AST structures using safe in-memory parsers without subprocess invocation.
3. For browser E2E validation, eliminate unconfined background server processes launched from the repository root; instead, connect to a pre-existing target endpoint or configured `TRACETEST_PLAYWRIGHT_TARGET_URL`.

### Consequences
- Eliminates host arbitrary code execution vulnerabilities arising from imported repositories.
- Guarantees deterministic, host-isolated static inspection.

---

## ADR-013: Git Clone Hardening, Token Masking via Askpass, and Uniform Ingestion

### Context
Repository import operations previously cloned repositories by embedding tokens directly in the URL (`https://x-access-token:{token}@github.com/...`). This persisted the secret token inside `.git/config` on disk and exposed it in process argument vectors (`argv`). In addition, the generic import path contained special-case branch shortcuts specifically for EchoBox, bypassing uniform directory isolation.

### Decision
1. Implement `run_hardened_git` in `app/services/git_client.py`: tokens are NEVER placed in argv or clone URLs. Instead, tokens are passed via a temporary `GIT_ASKPASS` script created with `0700` user permissions and immediately removed.
2. Enforce strict git flags on every git process invocation:
   - `-c core.hooksPath=/dev/null`
   - `-c protocol.file.allow=never`
   - `-c http.followRedirects=false`
   - `-c core.symlinks=false`
   - `-c submodule.recurse=false`
   - `GIT_TERMINAL_PROMPT=0`
   - `GIT_ALLOW_PROTOCOL=https`
3. Assert that `.git/config` never contains tokens post-clone, and enforce a repository size cap (`250 MB`) and file count cap (`10,000 files`).
4. Eliminate all target-specific shortcuts from `projects.py`; all imported repositories follow the deterministic `var/repos/{owner}_{repo_name}` layout.
5. In repository refresh, use `fetch_and_snapshot` to resolve and record the exact Git commit SHA without in-place destructive overwrites.

### Consequences
- Prevents token leakage into process listings (`ps`, `/proc`), audit logs, and on-disk git configuration files.
- Protects against malicious repository structures exploiting git submodules, symlink traversal, or custom hooks.
- Ensures identical, auditable ingestion behavior across all target repositories.

---

## ADR-015: Real SUT Execution Fidelity under Moto, Honest Provenance, and AI Secret Redaction

### Context
The `echobox_harness` originally relied on an in-memory Python simulation (`MemoryDynamo`, `EchoBoxMemoryBackend`) that reimplemented EchoBox logic rather than executing the target repository's code. This masked real-world defects such as unverified JWT signatures. In addition, requirement and defect provenance were ambiguous: requirements derived from code lacked commit SHA grounding and were treated as confirmed, while defects did not differentiate between static analysis findings and runtime test execution failures. Furthermore, prompts passed to cloud LLMs risked leaking host or cloud secrets.

### Decision
1. Implement `RealLambdaBackend` in `echobox_harness/backend.py`, which directly imports and invokes the actual `var/repos/{owner}_{repo_name}/backend/lambda_function.py` entrypoint inside an in-process mocked AWS environment powered by `moto` (`mock_aws()` with DynamoDB table `"EchoBox"`). Expose mode selection via `backend="real"` vs `backend="simulation"`.
2. Add `origin` (`documented`, `inferred_from_code`, `manual`), `source_commit_sha`, and `confidence` to `Requirement` records. Any requirement inferred from code starts in `status="needs_confirmation"` and requires human review/confirmation before automated test generation.
3. Add `source_paths` and line ranges to `Clause` records to establish exact code and documentation grounding.
4. Add `evidence_type` (`execution_failure`, `static_analysis`, `manual`) and `source_commit_sha` to `Defect` records. Explicitly prohibit labeling static analysis findings (such as unverified JWT token parsing) as runtime test failures without an actual failing test run.
5. Add pre-flight regex-based secret redaction (`redact_secrets`) across all LLM prompt pipelines in `app/llm/router.py`, masking AWS credentials, RSA/SSH private keys, GitHub tokens, Groq/Gemini API keys, and secret values before network transmission.

### Consequences
- High-fidelity execution of actual target repository code against AWS SDK contracts without incurring AWS billing or cloud network latency.
- Honest and auditable separation of documented specifications from inferred heuristics, and execution failures from static analysis findings.
- Zero cloud or host credential leaks in LLM traces or prompt logs.

---

## ADR-016: Service Modularization, SQLite Concurrency Discipline, and Cross-Project Isolation Boundaries

### Context
`repo_ingest.py` had expanded to over 2,000 lines, bundling URL validation, secret scanning, AST analysis, EchoBox test synthesis, and generic README parsing into a single monolithic file. In addition, background task crashes could leave runs in an unresumable running state, SQLite concurrency limits required empirical validation against thread pools, and multi-tenant project isolation required explicit endpoint-level regression guarantees.

### Decision
1. Modularize `repo_ingest` into a clean package under `app/services/repo_ingest/`: `url_validator.py`, `secret_scanner.py`, `ast_analyzer.py`, `echobox_derivation.py`, and `generic_derivation.py`. Re-export all public symbols via `__init__.py` for 100% backward compatibility.
2. Maintain SQLite WAL mode with `busy_timeout=10000`, short atomic transactions, and connection pre-ping. Verify that concurrent multi-threaded writes execute cleanly without `database is locked` errors.
3. Ensure startup reconciliation (`recover_interrupted()`) reliably marks orphaned `running` or `queued` tasks as `interrupted` with explanatory diagnostics.
4. Enforce project authorization boundaries across all entity endpoints (`requirements`, `test-cases`, `defects`, `executions`) returning 404 (NotFound) on cross-project ID guessing attempts by non-admin users.

### Consequences
- Clean separation of concerns and maintainability across ingestion pipelines.
- Full resilience to application restarts without dangling jobs.
- Mathematically verified tenant isolation preventing data leakage between independent repositories.






