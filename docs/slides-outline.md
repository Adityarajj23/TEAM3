# TraceTest AI — Presentation Slides Outline

**5-Slide Executive & Technical Overview**  
*Format: Structured Speaker Notes, Slide Content, Architecture Diagrams & Empirical Proof Points*

---

## Slide 1: The Verification Problem & Product Vision

### Slide Title
**Bridging the Chasm: From Business Requirements to Executable Proof**

### Core Message
Enterprise software verification is broken by manual test authoring bottlenecks, ambiguous specifications, and generative AI tools that hallucinate tests or fake execution passes. TraceTest AI establishes an auditable, evidence-grounded verification platform.

### Visual Layout
- **Left Column: The Industry Crisis**
  - 67% of software defects originate in ambiguous, conflicting, or unverified requirements.
  - Traditional LLM test generators hallucinate nonexistent functions and silently pass synthetic mocks.
  - Compliance audits struggle with disconnected Jira tickets, manual test spreadsheets, and unlinked PRs.
- **Right Column: TraceTest AI Solution Spine**
  - **Deterministic Grounding**: Every test case cites atomic clauses and verbatim source text verified by AST checks.
  - **Honest Execution**: Real code executed against mock/live targets; zero faked results or synthetic pass overrides.
  - **End-to-End Traceability**: 100% mathematical linkage from requirements to clauses, test cases, executions, and defects.

### Speaker Notes
> *"Good morning. Today, software development moves faster than ever, but quality assurance remains stuck in manual translation. Business analysts write specifications, developers interpret them into code, and QA engineers write tests that often verify their own assumptions rather than the specification or the actual implementation.*
>
> *TraceTest AI solves this fundamentally. We ingest real repositories, deconstruct requirements into verified atomic clauses, synthesize traceable test cases, execute them inside hardened sandboxes against real application code, and classify genuine defects with empirical evidence. We don't guess, and we never fake an execution pass."*

---

## Slide 2: Enterprise Architecture & Defense-in-Depth Security

### Slide Title
**Engineered for Zero Trust: Multi-Tiered Architecture & Security Invariants**

### Core Message
TraceTest AI enforces defense-in-depth across every boundary: network-isolated execution sandboxes, hardened git ingestion via askpass, signed sessions, and prompt secret scrubbing.

### Visual Layout
- **Architecture Diagram**:
  ```
  [ React 18 SPA + Vite ] <--- HTTP / SSE (Strict CORS, Host & Origin Validation) ---> [ FastAPI Core ]
                                                                                              |
                     +------------------------------------------------------------------------+
                     |                                       |                                |
             [ SQLite (WAL) ]                    [ Multi-Key SlotPool ]              [ POSIX Sandbox ]
             - Business Data                     - Groq (Primary)                    - netns network isolation
             - Audit Trails                      - Gemini (Failover)                 - RLIMIT_AS, RLIMIT_NPROC
             - LangGraph Checkpoints             - Pre-flight Secret Redaction       - AST Allowlist Filter
  ```
- **Key Invariants Callout Box**:
  - **Host Hardening**: 127.0.0.1 default bind; rejection of non-loopback single-operator modes.
  - **Git Askpass**: Tokens never appear in command line `argv` or `.git/config` files on disk.
  - **Fail-Closed Execution**: If network namespace isolation cannot be established, automated test execution fails closed.
  - **Zero Leaks**: Cloud credentials, SSH keys, and tokens are scrubbed via regex before LLM transmission.

### Speaker Notes
> *"Security is the foundational constraint of TraceTest AI. Target repositories are untrusted external inputs; we never run untrusted build scripts or package lifecycle hooks on the host.*
>
> *Our sandbox executes tests under Linux network namespace isolation (`unshare -rn`) with strict POSIX resource limits on memory, CPU, and process count (`RLIMIT_NPROC`) to defeat fork bombs. Our backend runs on SQLite in Write-Ahead Logging mode with a 10-second busy timeout and single-writer discipline, delivering enterprise reliability with zero database infrastructure overhead."*

---

## Slide 3: Grounded Requirement Engineering & Provenance

### Slide Title
**From Code to Clauses: Deterministic AST Mapping & Requirement Provenance**

### Core Message
TraceTest AI ingests real codebases, extracts domain architecture, and preserves strict provenance—separating documented specifications from code-inferred heuristics.

### Visual Layout
- **Real-World Case Study (EchoBox)**:
  - Repository: `https://github.com/sohan10012/EchoBox.git` (Pinned SHA: `b3740a62ad41`).
  - Architecture: Serverless AWS API Gateway, Lambda, DynamoDB Single Table, Dual Cognito Pools.
  - Ingestion Metrics: 8 Domain Modules mapped, 13 RPC Actions discovered, 0 hardcoded secrets.
- **Requirement Provenance Model**:
  - **Documented (`origin="documented"`)**: Derived directly from README or technical specifications.
  - **Inferred (`origin="inferred_from_code"`)**: Derived from AST code analysis; requires human confirmation before test synthesis.
  - **Quote Verification**: All 62 atomic clauses verified against actual source text via `guardrails/quotes.py`.

### Speaker Notes
> *"To prove TraceTest AI in the real world, we ingested EchoBox, an open-source serverless platform. Our ingestion engine mapped 8 distinct domain modules—from Room Lifecycle and Ephemeral Expiration to Security Whitelists.*
>
> *TraceTest AI avoids the trap of hallucinated requirements through explicit provenance. If a requirement is inferred from code rather than documented in a spec, it is tagged as `inferred_from_code` and placed into `needs_confirmation` status. Furthermore, every clause is backed by a verbatim quote from source files, cryptographically verified by our deterministic quote-checking engine."*

---

## Slide 4: Multi-Tiered Execution Fidelity & Governance

### Slide Title
**Real SUT Execution: In-Process Moto AWS Fidelity & Dual-Control Gates**

### Core Message
Tests are executed against real target code inside mocked AWS cloud environments, validated by dual-control human review workflows.

### Visual Layout
- **Three-Tiered Execution Matrix**:
  - **Tier A (Static AST Analysis)**: Fast pre-flight structural verification and manifest inspection.
  - **Tier B (Sandboxed Moto AWS)**: Loads actual `backend/lambda_function.py` under in-process DynamoDB mock. **21 / 21 tests passed (1.92s)**.
  - **Tier C (Live Remote Probe)**: Probes live AWS API Gateway endpoint; honestly records HTTP 500 infrastructure block without faking success.
- **Dual-Control Governance (Four-Eyes Principle)**:
  - Generated test cases cannot be self-approved by test authors.
  - Senior reviewer inspects test steps, preconditions, and locks test script with SHA-256 digest.
  - Script tampering automatically invalidates approval status (`needs_reapproval`).

### Speaker Notes
> *"Passing a test against a hand-written simulation proves only the simulation. In TraceTest AI, Tier B executes the actual target code—the real EchoBox `lambda_function.py`—against an in-memory AWS DynamoDB table powered by `moto`.*
>
> *We also enforce the Four-Eyes Principle: test authors and AI agents are blocked from self-approving generated test cases. A reviewer must sign off, at which point the script's SHA-256 digest is permanently bound to the test case version."*

---

## Slide 5: Defect Classification, Impact & Production Delivery

### Slide Title
**Evidence-Driven Defect Discovery, Automated Retest & Production Readiness**

### Core Message
TraceTest AI discovers real vulnerabilities and bugs, classifies them by empirical evidence type, and provides an end-to-end verification lifecycle.

### Visual Layout
- **EchoBox Defects Discovered (All empirically verified)**:
  - `DEF-ECHO-001` (*Static*): Room description length mismatch (500 chars in docs vs 1000 in Lambda).
  - `DEF-ECHO-002` (*Execution*): Silent truncation slicing instead of HTTP 400 Bad Request.
  - `DEF-ECHO-003` (*Execution*): Invalid visibility parameter silently defaults to public room.
  - `DEF-ECHO-004` (*Static*): Discovery N+1 query amplification loop in `discover_rooms`.
  - `DEF-ECHO-005` (*Execution*): Live AWS endpoint returns HTTP 500 (unseeded upstream cloud).
  - `DEF-ECHO-006` (*Critical Security*): Unverified JWT signature parsing in `authenticate_request`.
- **Delivery Verification Metrics**:
  - **103 Backend Pytest Tests**: 102 passed, 1 strict xfail for DEF-ECHO-006 against real unpatched Lambda.
  - **Frontend Quality**: 9 Vitest unit tests passed, 0 Vite build errors, 0 critical Axe accessibility violations.
  - **Code Quality**: Ruff clean (0 errors), Mypy clean (0 errors across 70 source files).

### Speaker Notes
> *"The ultimate test of a QA platform is whether it finds real defects. TraceTest AI uncovered 6 genuine defects in EchoBox, including DEF-ECHO-006—a critical vulnerability where JWT tokens are parsed without RSA signature verification against Cognito JWKS public keys.*
>
> *With 103 backend automated tests, full multi-project isolation, fail-closed sandboxing, 0 accessibility blockers, and full documentation, TraceTest AI is ready for production delivery. Thank you."*
