# Execution engine

Code: `backend/app/execution/sandbox.py`, `backend/app/services/executions.py`.

## What can run

A test is executable only when it is `approved`, its `validation_status` is `valid`, its automation is `pytest` or
`playwright`, and the SHA-256 of its current script equals the `script_hash` recorded at validation. Editing a test
creates a new version, resets it to `pending_review` and recomputes the hash. Every execution result stores the test
version and script hash that actually ran.

## Pytest sandbox

1. The AST allowlist is re-checked immediately before execution (only `pytest`, selected standard-library modules
   and `reference_hcm` public modules; no `os`, `sys`, `subprocess`, `socket`, `importlib`, `open`, `eval`, `exec`,
   `__import__`, dunder attributes, `global`, `while` or async code). Rejected scripts become `error` results with the
   reason.
2. A fresh temporary directory receives only the scripts, a copy of `reference_hcm/` and a guard `conftest.py` that
   disables socket creation and DNS lookups.
3. The child runs `python -I -B -m pytest -p no:cacheprovider --junitxml …` with an environment containing only
   `PATH`, `HOME` (the temp dir), `LANG`, `PYTHONHASHSEED`, `PYTHONDONTWRITEBYTECODE` and `REFERENCE_HCM_VERSION`.
   Server secrets are never inherited.
4. POSIX limits: address space (`TRACETEST_EXEC_MEMORY_MB`, default 512 MB), CPU seconds, 256 open files, 50 MB file
   size, no core dumps, new session.
5. On Linux, when unprivileged user namespaces are available, the child is started under `unshare -rn` (no network
   interfaces). Whether this applied is recorded in the execution's audit entry.
6. A wall-clock timeout (`TRACETEST_EXEC_TIMEOUT`, default 60 s) kills the whole process group; output beyond
   `TRACETEST_EXEC_MAX_OUTPUT` is truncated.
7. junit XML is parsed per test file; statuses map to `passed`, `failed`, `error`, `skipped`, `timed_out` (and
   `cancelled` when the user cancels). The full output and junit file are stored as artifacts with SHA-256 hashes.

Long runs execute in the in-process worker pool. Progress is exposed as a run record (`/api/v1/runs/{id}`) and a
Server-Sent Events stream (`/api/v1/runs/{id}/events`); the UI falls back to polling.

## Playwright

Environments of kind `web` have a `base_url`. Playwright scripts receive `page` and `base_url` fixtures; after each
test a screenshot and the browser console log are stored as artifacts. Browser runs need network access to the
target and skip the address-space limit (browsers reserve large virtual memory). Set
`TRACETEST_CHROMIUM_EXECUTABLE` if Playwright's bundled browsers are not installed. Verified in this build against
the TraceTest login page using a system Chrome.

## Windows

`resource` limits and network namespaces are unavailable. The engine still applies the AST allowlist, the socket
guard, a clean environment, a separate process group and the hard timeout. Treat Windows execution as
development-grade isolation.

## CI

`.github/workflows/ci.yml` initialises a workspace, exports approved PAY scripts (`scripts/export_tests.py`), runs
them against both engine builds and, when `TRACETEST_URL` and `TRACETEST_CI_TOKEN` secrets are set, posts the junit
to `POST /api/v1/ci/results`, which stores a `source = ci` execution with commit and branch. Regression comparison
between any two executions: `GET /api/v1/executions-compare?a=&b=`.
